"""LLM 节点

支持多种 LLM 提供商，可从数据库获取模型配置或使用自定义配置
支持变量传递和工具调用
"""

from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import Tool, StructuredTool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field, create_model
import re
import logging

from app.workflow.nodes.base_node import BaseNode, NodeResult
from app.config import get_settings
from app.workflow.langfuse_tracker import (
    get_langfuse_client,
    get_langchain_handler,
    create_span_direct,
    end_span,
)
from app.models.model_config import ModelConfig, ModelType
from app.models.tool import Tool as ToolModel, ToolType
from app.utils.crypto import decrypt_api_key
from app.tools.http_tool import HttpToolExecutor

logger = logging.getLogger(__name__)


class LLMNode(BaseNode):
    """LLM 调用节点，支持多种 LLM 提供商"""

    node_type = "llm"

    async def execute(self, state: Dict[str, Any]) -> NodeResult:
        """执行 LLM 调用

        Args:
            state: 工作流状态

        Returns:
            NodeResult
        """
        settings = get_settings()

        # 获取数据库会话（用于查询模型配置）
        db: Optional[AsyncSession] = state.get("_db")

        # 获取配置
        model_id = self.config.get("model_id")
        use_default = self.config.get("use_default", True)

        # 自定义配置（优先级最高）
        custom_api_key = self.config.get("api_key")
        custom_api_base = self.config.get("api_base")
        custom_model = self.config.get("model")

        # 尝试获取模型配置
        model_config = None
        api_key = None
        api_base = None
        model_name = None

        # 优先使用自定义配置
        if custom_api_key and custom_api_base and custom_model:
            api_key = custom_api_key
            api_base = custom_api_base
            model_name = custom_model
            logger.info(f"使用自定义 LLM 配置: {custom_model} @ {custom_api_base}")
        else:
            # 从数据库获取模型配置
            if db:
                model_config = await self._get_model_config(db, model_id, use_default)

            if model_config:
                api_key = decrypt_api_key(model_config.api_key)
                api_base = model_config.api_base
                model_name = model_config.model_name
                logger.info(f"使用数据库模型配置: {model_config.name} ({model_name})")
            else:
                # 使用默认环境变量配置
                api_key = settings.OPENAI_API_KEY
                api_base = settings.OPENAI_API_BASE
                model_name = self.config.get("model", "gpt-4o-mini")
                logger.warning(f"未找到模型配置，使用环境变量默认配置: {model_name}")

        # 获取温度参数
        temperature = self.config.get("temperature")
        if temperature is None and model_config and model_config.temperature:
            temperature = model_config.temperature / 10
        if temperature is None:
            temperature = 0.7

        # 获取最大 token
        max_tokens = self.config.get("max_tokens")
        if max_tokens is None and model_config and model_config.max_tokens:
            max_tokens = model_config.max_tokens
        if max_tokens is None:
            max_tokens = 4096

        # 超时时间
        timeout = model_config.timeout if model_config else self.config.get("timeout", 120)

        # 处理输入变量 - 从 state 中获取并解析
        input_variables = self.config.get("input_variables", [])
        state_vars = state.get("variables", {})
        logger.info(f"[LLMNode] input_variables config: {input_variables}")
        logger.info(f"[LLMNode] state variables: {state_vars}")

        resolved_variables = self._resolve_input_variables(state, input_variables)
        logger.info(f"[LLMNode] resolved_variables: {resolved_variables}")

        # 合并到 state 的 variables 中，用于模板渲染
        state_variables = state.get("variables", {})
        state_variables = {**state_variables, **resolved_variables}
        logger.info(f"[LLMNode] state_variables for template: {state_variables}")

        # 获取 prompt 模板
        system_prompt_template = self.config.get("system_prompt", "")
        prompt_template = self.config.get("prompt_template") or self.config.get("user_prompt", "")
        logger.info(f"[LLMNode] system_prompt_template: {system_prompt_template}")
        logger.info(f"[LLMNode] prompt_template: {prompt_template}")

        # 渲染模板（支持 ${variable} 和 {{variable}} 格式）
        system_prompt = self._render_template(system_prompt_template, state_variables) if system_prompt_template else ""
        user_prompt = self._render_template(prompt_template, state_variables) if prompt_template else ""

        logger.info(f"[LLMNode] Rendered system_prompt: {system_prompt}")
        logger.info(f"[LLMNode] Rendered user_prompt: {user_prompt}")

        # 如果没有配置 prompt，使用默认行为：将所有输入变量拼接
        if not user_prompt and resolved_variables:
            user_prompt = "\n".join([f"{k}: {v}" for k, v in resolved_variables.items() if v])
        elif not user_prompt:
            user_prompt = "请开始对话"

        logger.info(f"System prompt: {system_prompt[:100]}...")
        logger.info(f"User prompt: {user_prompt[:100]}...")

        # 初始化 LLM
        try:
            # 禁用 thinking mode，避免 reasoning_content 相关的 API 错误
            # DeepSeek 模型要求 reasoning_content 必须传回，禁用后可避免此问题
            llm = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,
                base_url=api_base,
                timeout=timeout,
                model_kwargs={
                    "extra_body": {"thinking": {"type": "disabled"}}
                },
            )
        except Exception as e:
            logger.error(f"LLM 初始化失败: {e}")
            return NodeResult(success=False, output={}, error=f"LLM 初始化失败: {str(e)}")

        # 处理工具绑定
        enable_tools = self.config.get("enable_tools", False)
        selected_tools = self.config.get("selected_tools", [])
        tools = []

        if enable_tools and selected_tools and db:
            tools = await self._load_tools(db, selected_tools)
            if tools:
                llm = llm.bind_tools(tools)
                logger.info(f"已绑定 {len(tools)} 个工具")

        # 构建消息
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=user_prompt))

        logger.info(f"Final system_prompt: {system_prompt}")
        logger.info(f"Final user_prompt: {user_prompt}")

        # Langfuse 追踪 (v4 SDK)
        span = None
        langchain_handler = None
        if settings.langfuse_available:
            # 创建 Span 记录节点执行
            span = create_span_direct(
                trace_id=state.get("execution_id"),
                node_type=self.node_type,
                node_name=self.node_id,
                input_data={
                    "model": model_name,
                    "system_prompt": system_prompt[:200] if system_prompt else "",
                    "user_prompt": user_prompt[:200] if user_prompt else "",
                },
                metadata={"temperature": temperature, "max_tokens": max_tokens},
            )
            # 获取 LangChain callback handler (v4 SDK)
            # 不再尝试获取已有 trace，直接创建 handler
            langchain_handler = get_langchain_handler()
            if langchain_handler:
                logger.info(f"Langfuse handler created for LLM call")

        # 调用 LLM
        try:
            # 构建 invoke 配置（包含 callbacks）
            invoke_config = {}
            if langchain_handler:
                invoke_config["callbacks"] = [langchain_handler]

            response = await llm.ainvoke(messages, config=invoke_config)
            output_text = response.content

            # 检查是否有工具调用请求
            tool_calls = []
            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_calls = response.tool_calls
                logger.info(f"LLM 请求调用 {len(tool_calls)} 个工具")

                # 执行工具调用
                tool_results = await self._execute_tool_calls(tool_calls, tools, db)
                if tool_results:
                    # 重要：必须正确处理 reasoning_content（thinking mode）
                    # 检查响应中是否有 reasoning_content
                    from langchain_core.messages import AIMessage, ToolMessage

                    reasoning_content = None
                    if hasattr(response, "reasoning_content"):
                        reasoning_content = response.reasoning_content
                    elif hasattr(response, "additional_kwargs"):
                        reasoning_content = response.additional_kwargs.get("reasoning_content")

                    # 构建 AIMessage，保留所有必要字段
                    ai_message_kwargs = {
                        "content": response.content or "",
                        "tool_calls": tool_calls,
                    }
                    if reasoning_content:
                        # 使用 additional_kwargs 传递 reasoning_content
                        ai_message_kwargs["additional_kwargs"] = {
                            "reasoning_content": reasoning_content
                        }

                    messages.append(AIMessage(**ai_message_kwargs))

                    # 然后添加工具结果消息
                    for tc, result in zip(tool_calls, tool_results):
                        messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

                    # 再次调用 LLM 获取最终响应
                    final_response = await llm.ainvoke(messages, config=invoke_config)
                    output_text = final_response.content
                    logger.info(f"工具调用后的最终响应: {output_text[:100]}...")

            # 提取 usage 元数据
            usage_metadata = self._extract_usage_metadata(response)

            # 结束 Span（如果启用）
            if span:
                end_span(span, output_data={
                    "success": True,
                    "output_preview": output_text[:100] if output_text else "",
                    "usage": usage_metadata,
                    "tool_calls_count": len(tool_calls),
                })

            # 构建输出
            raw_output = {
                "content": output_text,
                "model": model_name,
                "api_base": api_base,
                "provider": model_config.provider if model_config else "custom",
                "usage": usage_metadata,
                "tool_calls": len(tool_calls),
            }

            output_key = self.config.get("output_key", "result")
            output = {output_key: output_text, "_raw": raw_output}

            return NodeResult(success=True, output=output)

        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            # 结束 Span（如果启用）
            if span:
                end_span(span, output_data={}, metadata={"error": str(e)})
            return NodeResult(success=False, output={}, error=str(e))

    def _resolve_input_variables(self, state: Dict[str, Any], input_variables: List[Dict]) -> Dict[str, Any]:
        """解析输入变量

        Args:
            state: 工作流状态
            input_variables: 输入变量配置列表

        Returns:
            解析后的变量字典
        """
        resolved = {}
        variables = state.get("variables", {})
        node_outputs = state.get("node_outputs", {})

        logger.info(f"[LLMNode._resolve_input_variables] input_variables config: {input_variables}")
        logger.info(f"[LLMNode._resolve_input_variables] state.variables: {variables}")

        for var_config in input_variables:
            name = var_config.get("name")
            source = var_config.get("source", "")
            logger.info(f"[LLMNode._resolve_input_variables] Processing var: name={name}, source={source}")

            if not name:
                logger.warning(f"[LLMNode._resolve_input_variables] Skipping var_config without name: {var_config}")
                continue

            # 解析 source 引用，如 ${start-1.question}
            if source:
                value = self._parse_source_reference(source, variables, node_outputs)
                logger.info(f"[LLMNode._resolve_input_variables] Resolved value for '{name}': {value}")
                if value is not None:
                    resolved[name] = value
                else:
                    logger.warning(f"[LLMNode._resolve_input_variables] Could not resolve value for '{name}' from source '{source}'")

        logger.info(f"[LLMNode._resolve_input_variables] Final resolved: {resolved}")
        return resolved

    def _parse_source_reference(self, source: str, variables: Dict, node_outputs: Dict) -> Any:
        """解析变量引用

        Args:
            source: 引用字符串，如 "${start-1.question}" 或 "question"
            variables: 全局变量字典
            node_outputs: 节点输出字典

        Returns:
            变量值
        """
        if not source:
            return None

        # 处理 ${node_id.var_name} 格式（带 $ 前缀）
        match = re.match(r"\$\{([\w\-]+)\.(\w+)\}", source)
        if match:
            node_id = match.group(1)
            var_name = match.group(2)
            # 特殊处理 start 节点 - 从 variables 或 variables.input 获取
            if node_id.startswith("start"):
                # 先尝试直接从 variables 获取（API 直接传递方式）
                # 再尝试从 variables.input 获取（嵌套方式）
                value = variables.get(var_name) or \
                        variables.get("query") or \
                        variables.get("question") or \
                        variables.get("input", {}).get(var_name) or \
                        variables.get("input", {}).get("query") or \
                        variables.get("input", {}).get("question")
                logger.info(f"解析 start 节点变量: source={source}, var_name={var_name}, value={value}")
                return value
            node_output = node_outputs.get(node_id, {})
            return node_output.get(var_name)

        # 处理 node_id.var_name 格式（不带 $ 前缀）
        match = re.match(r"([\w\-]+)\.(\w+)", source)
        if match:
            node_id = match.group(1)
            var_name = match.group(2)
            if node_id.startswith("start"):
                # 同样的逻辑处理不带 $ 前缀的格式
                value = variables.get(var_name) or \
                        variables.get("query") or \
                        variables.get("question") or \
                        variables.get("input", {}).get(var_name) or \
                        variables.get("input", {}).get("query") or \
                        variables.get("input", {}).get("question")
                return value
            node_output = node_outputs.get(node_id, {})
            return node_output.get(var_name)

        # 处理 ${var_name} 格式（全局变量）
        match = re.match(r"\$\{(\w+)\}", source)
        if match:
            var_name = match.group(1)
            return variables.get(var_name)

        # 直接变量名
        return variables.get(source)

    def _render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """渲染模板，支持 ${variable} 和 {{variable}} 格式

        Args:
            template: 模板字符串
            variables: 变量字典

        Returns:
            渲染后的字符串
        """
        if not template:
            return ""

        # 替换 ${variable} 格式
        def replace_dollar_var(match):
            key = match.group(1)
            value = variables.get(key)
            return str(value) if value is not None else ""

        result = re.sub(r"\$\{(\w+)\}", replace_dollar_var, template)

        # 替换 {{variable}} 格式
        def replace_brace_var(match):
            key = match.group(1)
            value = variables.get(key)
            return str(value) if value is not None else ""

        result = re.sub(r"\{\{(\w+)\}\}", replace_brace_var, result)

        return result

    async def _load_tools(self, db: AsyncSession, tool_ids: List[str]) -> List[Tool]:
        """从数据库加载工具定义

        Args:
            db: 数据库会话
            tool_ids: 工具 ID 列表

        Returns:
            LangChain Tool 列表
        """
        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel, create_model

        tools = []
        try:
            result = await db.execute(
                select(ToolModel).where(ToolModel.id.in_(tool_ids), ToolModel.is_enabled == True)
            )
            tool_models = result.scalars().all()

            for tool_model in tool_models:
                # 构建 args_schema（从 input_schema 创建 Pydantic 模型）
                args_schema = None
                if tool_model.input_schema:
                    try:
                        # input_schema 是 JSON Schema 格式，转换为 Pydantic 模型
                        args_schema = self._create_args_schema_from_json_schema(
                            tool_model.name,
                            tool_model.input_schema
                        )
                        logger.info(f"工具 {tool_model.name} args_schema: {args_schema}")
                    except Exception as e:
                        logger.warning(f"创建 args_schema 失败: {e}")

                # 创建 LangChain StructuredTool
                tool = StructuredTool(
                    name=tool_model.name,
                    description=tool_model.description or "",
                    args_schema=args_schema,
                    func=lambda x: x,  # 占位函数，实际执行在 _execute_tool_calls
                )
                tools.append(tool)
                logger.info(f"加载工具: {tool_model.name}, args_schema={args_schema is not None}")
        except Exception as e:
            logger.warning(f"加载工具失败: {e}")

        return tools

    def _create_args_schema_from_json_schema(self, tool_name: str, json_schema: Dict[str, Any]) -> Optional[BaseModel]:
        """从 JSON Schema 创建 Pydantic 模型作为 args_schema

        Args:
            tool_name: 工具名称
            json_schema: JSON Schema 格式的输入定义

        Returns:
            Pydantic 模型类
        """
        if not json_schema or not json_schema.get("properties"):
            return None

        properties = json_schema.get("properties", {})
        required = json_schema.get("required", [])

        # 动态创建 Pydantic 模型字段
        fields = {}
        for prop_name, prop_def in properties.items():
            prop_type = prop_def.get("type", "string")
            prop_desc = prop_def.get("description", "")

            # 转换类型
            if prop_type == "string":
                field_type = str
            elif prop_type == "integer":
                field_type = int
            elif prop_type == "number":
                field_type = float
            elif prop_type == "boolean":
                field_type = bool
            elif prop_type == "array":
                field_type = list
            elif prop_type == "object":
                field_type = dict
            else:
                field_type = str

            # 是否必填
            if prop_name in required:
                fields[prop_name] = (field_type, Field(..., description=prop_desc))
            else:
                fields[prop_name] = (Optional[field_type], Field(None, description=prop_desc))

        # 动态创建模型类
        model_name = f"{tool_name.capitalize()}Args"
        return create_model(model_name, **fields)

    async def _execute_tool_calls(self, tool_calls: List[Dict], tools: List[Tool], db: AsyncSession) -> List[Any]:
        """执行工具调用

        Args:
            tool_calls: 工具调用请求列表
            tools: 工具列表（LangChain Tool，用于获取工具名称）
            db: 数据库会话

        Returns:
            工具执行结果列表
        """
        results = []
        http_executor = HttpToolExecutor()

        for tc in tool_calls:
            tool_name = tc.get("name")
            tool_args = tc.get("args", {})
            tool_call_id = tc.get("id", "")

            logger.info(f"执行工具: name={tool_name}, args={tool_args}, id={tool_call_id}")

            try:
                # 从数据库查找工具配置
                result = await db.execute(
                    select(ToolModel).where(ToolModel.name == tool_name, ToolModel.is_enabled == True)
                )
                tool_model = result.scalar_one_or_none()

                if not tool_model:
                    logger.warning(f"工具 {tool_name} 未找到或未启用")
                    results.append(f"错误：工具 {tool_name} 未找到或未启用")
                    continue

                logger.info(f"找到工具配置: type={tool_model.tool_type}, config={tool_model.config}")

                # 根据工具类型执行
                if tool_model.tool_type == ToolType.HTTP:
                    # 执行 HTTP 工具
                    tool_config = tool_model.config or {}

                    logger.info(f"HttpToolExecutor.execute: config={tool_config}, input_data={tool_args}")

                    execution_result = await http_executor.execute(
                        config=tool_config,
                        input_data=tool_args,
                    )

                    logger.info(f"HttpToolExecutor 返回: {execution_result}")

                    if execution_result.get("success"):
                        # 成功，返回输出
                        output = execution_result.get("output")
                        logger.info(f"工具 {tool_name} 执行成功: {str(output)[:200]}...")
                        results.append(output)
                    else:
                        # 失败，检查 output 和 error 字段
                        error = execution_result.get("error") or execution_result.get("output") or "未知错误"
                        logger.warning(f"工具 {tool_name} 执行失败: {error}")
                        results.append(f"工具执行失败: {error}")

                elif tool_model.tool_type == ToolType.MCP:
                    # MCP 工具执行（暂未实现）
                    logger.warning(f"MCP 工具 {tool_name} 暂未实现")
                    results.append(f"MCP 工具 {tool_name} 暂未实现")

                else:
                    logger.warning(f"未知工具类型: {tool_model.tool_type}")
                    results.append(f"未知工具类型: {tool_model.tool_type}")

            except Exception as e:
                logger.error(f"工具 {tool_name} 执行异常: {e}", exc_info=True)
                results.append(f"工具执行异常: {str(e)}")

        logger.info(f"_execute_tool_calls 返回: {results}")
        return results

    async def _get_model_config(self, db: AsyncSession, model_id: Optional[str], use_default: bool) -> Optional[ModelConfig]:
        """获取模型配置"""
        try:
            if model_id:
                result = await db.execute(
                    select(ModelConfig).where(
                        ModelConfig.id == model_id,
                        ModelConfig.type == ModelType.LLM,
                        ModelConfig.is_active == True
                    )
                )
                model = result.scalar_one_or_none()
                if model:
                    return model

            if use_default:
                result = await db.execute(
                    select(ModelConfig).where(
                        ModelConfig.type == ModelType.LLM,
                        ModelConfig.is_default == True,
                        ModelConfig.is_active == True
                    ).limit(1)
                )
                return result.scalar_one_or_none()

            return None
        except Exception as e:
            logger.error(f"获取模型配置失败: {e}")
            return None

    def _extract_usage_metadata(self, response) -> Dict[str, Any]:
        """提取 usage 元数据"""
        usage = {}

        if hasattr(response, "response_metadata") and response.response_metadata:
            token_usage = response.response_metadata.get("token_usage", {})
            if token_usage:
                usage["prompt_tokens"] = token_usage.get("prompt_tokens", 0)
                usage["completion_tokens"] = token_usage.get("completion_tokens", 0)
                usage["total_tokens"] = token_usage.get("total_tokens", 0)

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            meta = response.usage_metadata
            usage.setdefault("prompt_tokens", meta.get("input_tokens", 0))
            usage.setdefault("completion_tokens", meta.get("output_tokens", 0))
            usage.setdefault("total_tokens", meta.get("total_tokens", 0))

        return usage if usage else {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}