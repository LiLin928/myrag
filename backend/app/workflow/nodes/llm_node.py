"""LLM 节点

调用大语言模型生成响应
"""

from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import logging

from app.workflow.nodes.base_node import BaseNode, NodeResult
from app.config import get_settings
from app.workflow.langfuse_tracker import get_langfuse_client, get_langchain_handler

logger = logging.getLogger(__name__)


class LLMNode(BaseNode):
    """LLM 调用节点"""

    node_type = "llm"

    async def execute(self, state: Dict[str, Any]) -> NodeResult:
        """执行 LLM 调用

        Args:
            state: 工作流状态

        Returns:
            NodeResult
        """
        settings = get_settings()

        # 获取配置
        model = self.config.get("model", "gpt-4o-mini")
        system_prompt_template = self.config.get("system_prompt", "")
        # 支持 prompt_template（新名称）和 user_prompt（旧名称，保持向后兼容）
        prompt_template = self.config.get("prompt_template") or self.config.get("user_prompt", "")
        temperature = self.config.get("temperature", 0.7)
        max_tokens = self.config.get("max_tokens", 1024)

        # 创建 Langfuse handler（如果启用）
        langfuse_handler = None
        if settings.langfuse_available:
            try:
                langfuse = get_langfuse_client()
                if langfuse:
                    trace = langfuse.get_trace(state.get("execution_id"))
                    langfuse_handler = get_langchain_handler(trace)
            except Exception as e:
                logger.warning(f"Langfuse handler creation failed: {e}")

        callbacks = [langfuse_handler] if langfuse_handler else []

        # 构建系统提示（支持变量替换）
        system_prompt = self.render_template(system_prompt_template, state) if system_prompt_template else ""

        # 构建用户提示（替换变量）
        user_prompt = self.render_template(prompt_template, state)

        # 初始化 LLM
        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE,
            callbacks=callbacks,
        )

        # 构建消息
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=user_prompt))

        # 调用 LLM
        try:
            response = await llm.ainvoke(
                messages,
                config={"callbacks": callbacks}
            )
            output_text = response.content

            # 提取 usage 元数据
            usage_metadata = self._extract_usage_metadata(response)

            # 构建原始输出（包含内容和元数据）
            raw_output = {
                "content": output_text,
                "model": model,
                "usage": usage_metadata,
            }

            # 设置输出变量（支持旧版 output_key 配置）
            output_key = self.config.get("output_key", "llm_response")

            # 构建基础输出
            output = {output_key: output_text, "_raw": raw_output}

            # 如果配置了 output_variables，使用 map_output_variables 进行映射
            output_variables = self.config.get("output_variables")
            if output_variables and isinstance(output_variables, dict):
                # 先构建完整的输出字典
                full_output = {output_key: output_text, "_raw": raw_output}
                # 映射输出变量
                output = self.map_output_variables(full_output, output_variables)
                # 确保保留 _raw 元数据
                if "_raw" not in output:
                    output["_raw"] = raw_output

            return NodeResult(
                success=True,
                output=output,
            )

        except Exception as e:
            return NodeResult(
                success=False,
                output={},
                error=str(e),
            )

    def _extract_usage_metadata(self, response) -> Dict[str, Any]:
        """从 LLM 响应中提取 usage 元数据

        Args:
            response: LangChain LLM 响应对象

        Returns:
            Usage 元数据字典
        """
        usage = {}

        # 尝试从 response_metadata 中提取
        if hasattr(response, "response_metadata") and response.response_metadata:
            token_usage = response.response_metadata.get("token_usage", {})
            if token_usage:
                usage["prompt_tokens"] = token_usage.get("prompt_tokens", 0)
                usage["completion_tokens"] = token_usage.get("completion_tokens", 0)
                usage["total_tokens"] = token_usage.get("total_tokens", 0)

        # 尝试从 usage_metadata 中提取（LangChain 新版）
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            meta = response.usage_metadata
            if "prompt_tokens" not in usage:
                usage["prompt_tokens"] = meta.get("input_tokens", 0)
            if "completion_tokens" not in usage:
                usage["completion_tokens"] = meta.get("output_tokens", 0)
            if "total_tokens" not in usage:
                usage["total_tokens"] = meta.get("total_tokens", 0)

        return usage if usage else {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}