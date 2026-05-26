"""RAG 检索节点

从知识库检索相关文档片段
"""

from typing import Dict, Any, Optional, List
import logging

from app.workflow.nodes.base_node import BaseNode, NodeResult
from app.rag.retrieval.hybrid_retriever import HybridRetriever
from app.rag.retrieval.pgvector_retriever import PGVectorRetriever
from app.workflow.langfuse_tracker import create_span_direct, end_span
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

        # 打印完整配置和状态，用于诊断
        logger.warning(f"RAGNode {self.node_id} CONFIG DEBUG: {self.config}")  # 使用 WARNING 级别确保显示
        logger.warning(f"RAGNode {self.node_id} STATE variables: {state.get('variables', {})}")
        logger.warning(f"RAGNode {self.node_id} STATE node_outputs keys: {list(state.get('node_outputs', {}).keys())}")

        # 获取配置
        knowledge_base_id = self.config.get("knowledge_base_id") or self.config.get("project_id")
        top_k = self.config.get("top_k", 5)
        score_threshold = self.config.get("score_threshold", 0.0)
        # 支持 query_source（前端配置）和 query_variable（旧格式）
        query_source = self.config.get("query_source", "") or self.config.get("query_variable", "")
        query_template = self.config.get("query", "")
        output_variables = self.config.get("output_variables", {})
        search_type = self.config.get("search_type", "hybrid")
        output_key = self.config.get("output_key", "contexts")

        logger.warning(f"RAGNode {self.node_id} RESOLVED VALUES: knowledge_base_id={knowledge_base_id}, query_source={query_source}, query_template={query_template}")

        # 解析查询变量
        query = await self._resolve_query(state, query_source, query_template)
        logger.info(f"RAGNode {self.node_id} resolved query: {query}")

        if not query:
            return NodeResult(
                success=False,
                output={},
                error="Query is empty. Please provide query_source or query.",
            )

        # 创建 Span（如果启用）
        span = None
        if settings.langfuse_available:
            span = create_span_direct(
                trace_id=state.get("execution_id"),
                node_type=self.node_type,
                node_name=self.node_id,
                input_data={"query": query, "knowledge_base_id": knowledge_base_id, "search_type": search_type},
                metadata={"top_k": top_k, "score_threshold": score_threshold},
            )

        # 执行检索
        try:
            # 获取知识库配置中的 embedding 模型和配置
            embedding_model_name, embedding_config = await self._get_kb_embedding_model(knowledge_base_id, state)
            logger.warning(f"RAGNode {self.node_id} using embedding_model: {embedding_model_name}, config: {embedding_config}")

            # 创建检索器（传入 embedding 配置）
            retriever = self._get_retriever(
                knowledge_base_id=knowledge_base_id,
                top_k=top_k,
                score_threshold=score_threshold,
                search_type=search_type,
                embedding_model=embedding_model_name,
                embedding_config=embedding_config,
            )

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
        - ${start-1.question}: 开始节点的输出

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
            logger.info(f"RAGNode resolving var_path: {var_path}")

            # 解析路径（支持 node_id.output_key 格式）
            parts = var_path.split('.', 1)

            if len(parts) == 1:
                # 简单变量名，从输入变量获取
                variables = state.get("variables", {})
                value = variables.get(parts[0])
                logger.info(f"RAGNode simple variable: {parts[0]} = {value}")
                return value

            node_id, output_key = parts
            logger.info(f"RAGNode parsing: node_id={node_id}, output_key={output_key}")

            # 特殊处理 start 节点 - 从 variables 获取
            if node_id.startswith("start"):
                variables = state.get("variables", {})
                # 尝试多种可能的键名，并处理变量名映射
                # question -> query 的常见映射
                if output_key == "question":
                    value = variables.get("question") or variables.get("query")
                else:
                    value = variables.get(output_key) or \
                            variables.get("question") or \
                            variables.get("query") or \
                            variables.get("input", {}).get(output_key)
                logger.warning(f"RAGNode start node: output_key={output_key}, resolved value={value}")
                return value

            # 节点输出引用: ${node_id.output_key}
            node_outputs = state.get("node_outputs", {})
            node_output = node_outputs.get(node_id, {})
            value = node_output.get(output_key)
            logger.info(f"RAGNode node output: {node_id}.{output_key} = {value}")
            return value

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

        result = var_pattern.sub(replace_var, expression)
        logger.info(f"RAGNode resolved expression: {expression} -> {result}")
        return result

    async def _get_kb_embedding_model(
        self,
        knowledge_base_id: Optional[str],
        state: Dict[str, Any],
    ) -> tuple[Optional[str], Optional[Any]]:
        """获取知识库配置的 embedding 模型和配置

        Args:
            knowledge_base_id: 知识库 ID
            state: 工作流状态（包含 _db）

        Returns:
            (embedding_model_name, embedding_config) 元组
        """
        if not knowledge_base_id:
            return None, None

        db = state.get("_db")
        if not db:
            logger.warning(f"RAGNode {self.node_id}: no db session, using default embedding")
            return None, None

        try:
            from sqlalchemy import select
            from app.models.knowledge_base import KnowledgeBase
            from app.models.model_config import ModelConfig, ModelType
            from app.rag.embedding.embedding_models import EmbeddingModelConfig

            # 获取知识库配置
            result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id)
            )
            kb = result.scalar_one_or_none()

            if kb:
                kb_embedding_model = kb.embedding_model
                logger.warning(f"RAGNode {self.node_id}: KB embedding_model = {kb_embedding_model}")

                # 如果知识库配置了 embedding_model，尝试从数据库获取对应的 ModelConfig
                if kb_embedding_model:
                    try:
                        model_result = await db.execute(
                            select(ModelConfig).where(
                                ModelConfig.model_name == kb_embedding_model,
                                ModelConfig.type == ModelType.EMBEDDING,
                                ModelConfig.is_active == True
                            )
                        )
                        model_config = model_result.scalar_one_or_none()

                        if model_config:
                            logger.warning(f"RAGNode {self.node_id}: Found ModelConfig for {kb_embedding_model}, api_base={model_config.api_base}")
                            # 构建 EmbeddingModelConfig
                            from app.utils.crypto import decrypt_api_key
                            api_key = decrypt_api_key(model_config.api_key) if model_config.api_key else None

                            embedding_config = EmbeddingModelConfig(
                                provider=model_config.provider or "openai",
                                model_name=model_config.model_name,
                                api_base=model_config.api_base,
                                api_key=api_key,
                                dimension=model_config.dimension or 1536,
                            )
                            return kb_embedding_model, embedding_config
                        else:
                            logger.warning(f"RAGNode {self.node_id}: No ModelConfig found for {kb_embedding_model}")

                    except Exception as e:
                        logger.warning(f"RAGNode {self.node_id}: Failed to get ModelConfig: {e}")

                return kb_embedding_model, None

        except Exception as e:
            logger.warning(f"RAGNode {self.node_id}: failed to get KB config: {e}")

        return None, None

    def _get_retriever(
        self,
        knowledge_base_id: Optional[str],
        top_k: int,
        score_threshold: float,
        search_type: str,
        embedding_model: Optional[str] = None,
        embedding_config: Optional[Any] = None,
    ):
        """获取检索器

        Args:
            knowledge_base_id: 知识库 ID（可以是 UUID 字符串或数字）
            top_k: 返回结果数量
            score_threshold: 相似度阈值
            search_type: 检索类型（vector/keyword/hybrid）
            embedding_model: embedding 模型名称
            embedding_config: embedding 配置对象

        Returns:
            检索器实例
        """
        # 不强制转换为 int，让检索器自己处理 UUID 格式
        if search_type == "vector":
            return PGVectorRetriever(
                knowledge_base_id=knowledge_base_id,
                embedding_model=embedding_model,
                embedding_config=embedding_config,
                top_k=top_k,
                score_threshold=score_threshold,
            )
        elif search_type == "keyword":
            # keyword 搜索使用 HybridRetriever 的纯关键词模式
            return HybridRetriever(
                knowledge_base_id=knowledge_base_id,
                embedding_model=embedding_model,
                embedding_config=embedding_config,
                top_k=top_k,
                score_threshold=score_threshold,
                vector_weight=0.0,  # 纯关键词
                keyword_weight=1.0,
            )
        else:
            # hybrid 模式（默认）
            return HybridRetriever(
                knowledge_base_id=knowledge_base_id,
                embedding_model=embedding_model,
                embedding_config=embedding_config,
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