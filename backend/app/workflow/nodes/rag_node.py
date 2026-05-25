"""RAG 检索节点

从知识库检索相关文档片段
"""

from typing import Dict, Any, Optional, List
import logging

from app.workflow.nodes.base_node import BaseNode, NodeResult
from app.rag.retrieval.hybrid_retriever import HybridRetriever
from app.rag.retrieval.pgvector_retriever import PGVectorRetriever
from app.workflow.langfuse_tracker import create_span, end_span
from app.config import get_settings

logger = logging.getLogger(__name__)


class RAGNode(BaseNode):
    """RAG 检索节点

    支持配置项：
    - knowledge_base_id: 知识库 ID（原 project_id）
    - query_variable: 查询变量引用（如 ${query}）
    - query: 查询文本模板（支持 ${variable} 变量）
    - search_type: 检索类型（vector/keyword/hybrid）
    - top_k: 返回结果数量
    - score_threshold: 相似度阈值
    - output_variables: 输出变量映射
    """

    node_type = "rag"

    async def execute(self, state: Dict[str, Any]) -> NodeResult:
        """执行 RAG 检索

        Args:
            state: 工作流状态

        Returns:
            NodeResult
        """
        settings = get_settings()

        # 获取配置
        knowledge_base_id = self.config.get("knowledge_base_id") or self.config.get("project_id")
        top_k = self.config.get("top_k", 5)
        score_threshold = self.config.get("score_threshold", 0.0)
        query_variable = self.config.get("query_variable", "")
        query_template = self.config.get("query", "")
        output_variables = self.config.get("output_variables", {})
        search_type = self.config.get("search_type", "hybrid")
        output_key = self.config.get("output_key", "contexts")

        # 解析查询变量
        query = await self._resolve_query(state, query_variable, query_template)

        if not query:
            return NodeResult(
                success=False,
                output={},
                error="Query is empty. Please provide query or query_variable.",
            )

        # 创建 Span（如果启用）
        span = None
        if settings.langfuse_available:
            span = create_span(
                trace_id=state.get("execution_id"),
                node_type=self.node_type,
                node_name=self.node_id,
                input_data={"query": query, "knowledge_base_id": knowledge_base_id, "search_type": search_type},
                metadata={"top_k": top_k, "score_threshold": score_threshold},
            )

        # 初始化检索器
        retriever = self._get_retriever(
            knowledge_base_id=knowledge_base_id,
            top_k=top_k,
            score_threshold=score_threshold,
            search_type=search_type,
        )

        # 执行检索
        try:
            results = await retriever.search(query)

            # 格式化输出
            contexts = [
                {
                    "content": r["content"],
                    "source": r.get("document_id"),
                    "score": r["score"],
                    "metadata": r.get("metadata", {}),
                }
                for r in results
            ]

            # 构建上下文文本
            context_text = "\n\n".join([c["content"] for c in contexts])

            # 提取 top_scores 用于后续分析
            top_scores = [r["score"] for r in results[:5]] if results else []

            # 构建原始输出
            raw_output = {
                output_key: contexts,
                f"{output_key}_text": context_text,
                "query": query,
                "results_count": len(contexts),
                "top_scores": top_scores,
                "search_type": search_type,
            }

            # 应用输出变量映射
            final_output = self._apply_output_variables(raw_output, output_variables)

            # 结束 Span
            if span:
                end_span(span, output_data={"results_count": len(contexts), "top_scores": top_scores})

            return NodeResult(
                success=True,
                output=final_output,
            )

        except Exception as e:
            # 结束 Span（错误）
            if span:
                end_span(span, output_data={}, metadata={"error": str(e)})
            return NodeResult(
                success=False,
                output={},
                error=str(e),
            )

    async def _resolve_query(
        self,
        state: Dict[str, Any],
        query_variable: str,
        query_template: str,
    ) -> Optional[str]:
        """解析查询变量

        优先使用 query_variable，如果为空则使用 query_template

        Args:
            state: 工作流状态
            query_variable: 查询变量引用（如 ${query}）
            query_template: 查询文本模板

        Returns:
            解析后的查询字符串
        """
        # 如果有 query_variable，优先解析变量引用
        if query_variable:
            return self._resolve_variable(query_variable, state)

        # 否则使用 query_template 进行模板渲染
        if query_template:
            return self.render_template(query_template, state)

        return None

    def _resolve_variable(self, expression: str, state: Dict[str, Any]) -> Optional[str]:
        """解析变量引用表达式

        支持 ${variable} 格式的变量引用：
        - ${query}: 输入变量
        - ${node_id.output}: 节点输出变量

        Args:
            expression: 变量引用表达式
            state: 工作流状态

        Returns:
            解析后的值
        """
        import re

        # 变量引用模式: ${variable_name} 或 ${node_id.output_key}
        var_pattern = re.compile(r'\$\{([^}]+)\}')

        def get_variable_value(var_path: str) -> Any:
            """获取变量值"""
            # 解析路径（支持 node_id.output_key 格式）
            parts = var_path.split('.', 1)

            if len(parts) == 1:
                # 简单变量名，从输入变量获取
                variables = state.get("variables", {})
                return variables.get(parts[0])
            else:
                # 节点输出引用: ${node_id.output_key}
                node_id, output_key = parts
                node_outputs = state.get("node_outputs", {})
                node_output = node_outputs.get(node_id, {})
                return node_output.get(output_key)

        # 检查整个表达式是否是单个变量引用
        match = var_pattern.fullmatch(expression)
        if match:
            var_path = match.group(1)
            value = get_variable_value(var_path)
            return str(value) if value is not None else None

        # 替换所有变量引用
        def replace_var(match):
            var_path = match.group(1)
            value = get_variable_value(var_path)
            return str(value) if value is not None else ""

        return var_pattern.sub(replace_var, expression)

    def _get_retriever(
        self,
        knowledge_base_id: Optional[int],
        top_k: int,
        score_threshold: float,
        search_type: str,
    ):
        """获取检索器

        Args:
            knowledge_base_id: 知识库 ID
            top_k: 返回结果数量
            score_threshold: 相似度阈值
            search_type: 检索类型（vector/keyword/hybrid）

        Returns:
            检索器实例
        """
        if search_type == "vector":
            return PGVectorRetriever(
                project_id=int(knowledge_base_id) if knowledge_base_id else None,
                top_k=top_k,
                score_threshold=score_threshold,
            )
        elif search_type == "keyword":
            # keyword 搜索使用 HybridRetriever 的纯关键词模式
            return HybridRetriever(
                project_id=int(knowledge_base_id) if knowledge_base_id else None,
                top_k=top_k,
                score_threshold=score_threshold,
                vector_weight=0.0,  # 纯关键词
                keyword_weight=1.0,
            )
        else:
            # hybrid 模式（默认）
            return HybridRetriever(
                project_id=int(knowledge_base_id) if knowledge_base_id else None,
                top_k=top_k,
                score_threshold=score_threshold,
            )

    def _apply_output_variables(
        self,
        output: Dict[str, Any],
        output_variables: Dict[str, str],
    ) -> Dict[str, Any]:
        """应用输出变量映射

        Args:
            output: 原始输出
            output_variables: 输出变量映射 {原变量名: 新变量名}

        Returns:
            映射后的输出
        """
        if not output_variables:
            return output

        mapped_output = {}
        for key, value in output.items():
            if key in output_variables:
                new_key = output_variables[key]
                mapped_output[new_key] = value
            else:
                mapped_output[key] = value

        return mapped_output