"""工具调用节点"""

from typing import Dict, Any
import re
import logging

from app.workflow.nodes.base_node import BaseNode, NodeResult
from app.tools.tool_registry import tool_registry
from app.services.tool_service import tool_service
from app.db import async_session_factory
from app.workflow.langfuse_tracker import create_span_direct, end_span
from app.config import get_settings

logger = logging.getLogger(__name__)


class ToolNode(BaseNode):
    """工具调用节点

    支持两种模式:
    1. 通过 tool_id 调用 Tool 表中注册的工具 (HTTP 工具等)
    2. 通过 tool_name 调用 tool_registry 中注册的内置工具 (向后兼容)
    """

    node_type = "tool"

    async def execute(self, state: Dict[str, Any]) -> NodeResult:
        """执行工具调用

        优先检查 tool_id，存在则调用注册工具;
        否则使用 tool_name 调用内置工具 (向后兼容)
        """
        settings = get_settings()
        tool_id = self.config.get("tool_id")
        tool_name = self.config.get("tool_name", "")

        # 创建 Span（如果启用）
        span = None
        if settings.langfuse_available:
            span = create_span_direct(
                trace_id=state.get("execution_id"),
                node_type=self.node_type,
                node_name=self.node_id,
                input_data={"tool_id": tool_id, "tool_name": tool_name},
                metadata={},
            )

        if tool_id:
            result = await self._execute_registered_tool(state)
        else:
            result = await self._execute_registry_tool(state)

        # 结束 Span
        if span:
            end_span(span, output_data={"success": result.success}, metadata={"error": result.error if not result.success else None})

        return result

    async def _execute_registered_tool(self, state: Dict[str, Any]) -> NodeResult:
        """执行 Tool 表中注册的工具

        Args:
            state: 工作流状态

        Returns:
            NodeResult
        """
        tool_id = self.config.get("tool_id")
        if not tool_id:
            return NodeResult(
                success=False,
                output={},
                error="tool_id is required for registered tool execution",
            )

        # 构建输入数据
        input_data = self._build_input_data(state)

        # 获取输出映射配置
        output_mapping = self.config.get("output_mapping", {})
        output_key = self.config.get("output_key", "tool_result")

        try:
            # 使用数据库 session 执行工具
            async with async_session_factory() as db:
                result = await tool_service.execute_tool(db, tool_id, input_data)

            # 检查执行结果
            if not result.get("success", False):
                error_msg = result.get("error", "Tool execution failed")
                logger.error(f"Tool {tool_id} execution failed: {error_msg}")
                return NodeResult(
                    success=False,
                    output={},
                    error=error_msg,
                )

            # 应用输出映射
            output_data = result.get("output", result)
            mapped_output = self._apply_output_mapping(output_data, output_mapping)

            return NodeResult(
                success=True,
                output={output_key: mapped_output},
            )

        except Exception as e:
            logger.exception(f"Tool {tool_id} execution error: {e}")
            return NodeResult(
                success=False,
                output={},
                error=str(e),
            )

    async def _execute_registry_tool(self, state: Dict[str, Any]) -> NodeResult:
        """执行内置工具 (向后兼容)

        Args:
            state: 工作流状态

        Returns:
            NodeResult
        """
        tool_name = self.config.get("tool_name", "")
        tool_args = self.config.get("args", {})
        output_key = self.config.get("output_key", "tool_result")

        # 获取工具
        tool = tool_registry.get_tool_by_name(tool_name)
        if not tool:
            return NodeResult(
                success=False,
                output={},
                error=f"Tool '{tool_name}' not found",
            )

        # 渲染参数
        rendered_args = self._render_args(tool_args, state)

        # 调用工具
        try:
            result = await tool.ainvoke(rendered_args)

            return NodeResult(
                success=True,
                output={output_key: result},
            )

        except Exception as e:
            return NodeResult(
                success=False,
                output={},
                error=str(e),
            )

    def _build_input_data(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """构建工具输入数据

        支持多种配置格式:
        - tool_inputs: 前端节点配置面板传入的参数
        - input_mapping: 参数映射配置
        - args: 兼容旧格式

        Args:
            state: 工作流状态

        Returns:
            构建好的输入数据字典
        """
        input_data = {}

        # 优先使用 tool_inputs（前端配置）
        tool_inputs = self.config.get("tool_inputs", {})
        if tool_inputs:
            # 渲染 tool_inputs 中的变量引用
            for param_name, value in tool_inputs.items():
                if isinstance(value, str) and value.startswith("${"):
                    # 解析变量引用 ${node_id.output}
                    rendered_value = self._resolve_variable_reference(value, state)
                    input_data[param_name] = rendered_value
                else:
                    input_data[param_name] = value
            logger.info(f"ToolNode _build_input_data from tool_inputs: {input_data}")
            return input_data

        # 其次使用 input_mapping
        input_mapping = self.config.get("input_mapping", {})
        if input_mapping:
            for param_name, source_path in input_mapping.items():
                value = self._get_value_by_path(state, source_path)
                if value is not None:
                    input_data[param_name] = value
            logger.info(f"ToolNode _build_input_data from input_mapping: {input_data}")
            return input_data

        # 最后使用 args（兼容旧格式）
        args = self.config.get("args", {})
        if args:
            rendered_args = self._render_args(args, state)
            logger.info(f"ToolNode _build_input_data from args: {rendered_args}")
            return rendered_args

        return input_data

    def _resolve_variable_reference(self, expression: str, state: Dict[str, Any]) -> Any:
        """解析变量引用表达式

        支持 ${node_id.output} 格式的变量引用

        Args:
            expression: 变量引用表达式（如 "${llm-1.result}"）
            state: 工作流状态

        Returns:
            解析后的值
        """
        import re

        # 变量引用模式: ${variable_name} 或 ${node_id.output_key}
        match = re.match(r'\$\{([^}]+)\}', expression)
        if not match:
            return expression

        var_path = match.group(1)
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

    def _get_value_by_path(self, data: Dict[str, Any], path: str) -> Any:
        """根据路径从数据中获取值

        支持格式:
        - "variables.key" - 从变量中获取
        - "node_outputs.node_id.field" - 从节点输出中获取
        - "{{key}}" - 模板变量格式 (兼容旧模式)

        Args:
            data: 数据字典
            path: 路径字符串

        Returns:
            找到的值，如果不存在返回 None
        """
        if not path:
            return None

        # 检查是否是模板变量格式 {{key}}
        match = re.match(r"\{\{(\w+)\}\}", path)
        if match:
            key = match.group(1)
            return self.get_input_variable(data, key)

        # 使用基类的路径提取方法
        return self._extract_by_path(data, path)

    def _apply_output_mapping(
        self, output_data: Any, output_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """应用输出映射

        将工具返回的数据按照 output_mapping 提取需要的字段

        Args:
            output_data: 工具返回的原始数据
            output_mapping: 输出映射配置 {输出变量名: 数据路径}
                例如: {"title": "data.title", "items": "data.items"}

        Returns:
            映射后的输出字典
        """
        if not output_mapping:
            # 没有配置映射，返回原始数据
            if isinstance(output_data, dict):
                return output_data
            return {"result": output_data}

        mapped_output = {}
        for output_name, source_path in output_mapping.items():
            value = self._get_nested_value(output_data, source_path)
            if value is not None:
                mapped_output[output_name] = value

        return mapped_output

    def _get_nested_value(self, data: Any, path: str) -> Any:
        """从嵌套数据结构中获取值

        支持路径格式: "data.items.0.name" 或 "result.body"

        Args:
            data: 数据 (dict 或 list)
            path: 点号分隔的路径

        Returns:
            找到的值，如果不存在返回 None
        """
        if not path:
            return data

        keys = path.split(".")
        current = data

        for key in keys:
            if current is None:
                return None

            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list):
                try:
                    index = int(key)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        return None
                except ValueError:
                    return None
            else:
                return None

        return current

    def _render_args(self, args: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """渲染参数 (向后兼容方法)

        Args:
            args: 参数字典
            state: 工作流状态

        Returns:
            渲染后的参数字典
        """
        def replace_value(value):
            if isinstance(value, str):
                return self.render_template(value, state)
            return value

        return {k: replace_value(v) for k, v in args.items()}