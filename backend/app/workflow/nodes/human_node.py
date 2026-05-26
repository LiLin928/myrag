"""人工介入节点

工作流暂停，等待用户输入，支持完整的审批配置
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from app.workflow.nodes.base_node import BaseNode, NodeResult
from app.workflow.langfuse_tracker import create_span_direct, end_span
from app.config import get_settings

logger = logging.getLogger(__name__)


# 默认动作选项
DEFAULT_ACTION_OPTIONS = [
    {"label": "批准", "value": "approve"},
    {"label": "拒绝", "value": "reject"},
]

# 默认输入字段
DEFAULT_INPUT_FIELDS = [
    {"name": "comment", "type": "text", "required": True, "label": "审批意见"},
]


class HumanNode(BaseNode):
    """人工介入节点，支持完整的审批配置"""

    node_type = "human"

    async def execute(self, state: Dict[str, Any]) -> NodeResult:
        """执行人工介入

        Args:
            state: 工作流状态

        Returns:
            NodeResult（状态暂停，包含审批配置）
        """
        settings = get_settings()

        # 获取基础配置
        title = self.config.get("title", "人工审批")
        description = self.config.get("description", "请审核以下内容并做出决定")

        # 获取输入展示配置（用于向用户展示数据）
        input_display_template = self.config.get("input_display", "")

        # 获取动作选项配置
        action_options = self.config.get("action_options", DEFAULT_ACTION_OPTIONS)

        # 获取输入字段配置
        input_fields = self.config.get("input_fields", DEFAULT_INPUT_FIELDS)

        # 获取超时配置
        timeout_hours = self.config.get("timeout_hours", 24)  # 默认24小时
        timeout_action = self.config.get("timeout_action", "reject")  # 超时默认动作

        # 获取输出变量配置
        output_variables = self.config.get("output_variables", [])

        # 获取旧版兼容配置
        prompt_template = self.config.get("prompt", "")
        timeout_seconds = self.config.get("timeout", 300)  # 旧版秒数配置
        output_key = self.config.get("output_key", "human_input")

        # 计算超时时间（优先使用 timeout_hours）
        if timeout_hours:
            timeout_seconds = int(timeout_hours * 3600)

        # 渲染输入展示模板
        input_display = ""
        if input_display_template:
            input_display = self.render_template(input_display_template, state)
        elif prompt_template:
            # 兼容旧版 prompt 配置
            input_display = self.render_template(prompt_template, state)

        # 获取上下文信息
        user_id = state.get("user_id", "")
        execution_id = state.get("execution_id", "")

        # 计算过期时间
        expires_at = None
        if timeout_seconds and timeout_seconds > 0:
            expires_at = (datetime.now() + timedelta(seconds=timeout_seconds)).isoformat()

        # 创建 Span（如果启用）
        span = None
        if settings.langfuse_available:
            span = create_span_direct(
                trace_id=execution_id,
                node_type=self.node_type,
                node_name=self.node_id,
                input_data={"title": title},
                metadata={"timeout_hours": timeout_hours, "action_options_count": len(action_options)},
            )

        # 构建输出变量映射
        output_mapping = {}
        for var in output_variables:
            var_name = var.get("name", "")
            var_source = var.get("source", "")
            if var_name and var_source:
                output_mapping[var_name] = var_source

        output = {
            "status": "paused",
            "node_type": "human",
            "human_node_id": self.node_id,

            # 标题和描述
            "title": title,
            "description": description,

            # 输入展示内容
            "input_display": input_display,

            # 动作选项
            "action_options": action_options,

            # 输入字段配置
            "input_fields": input_fields,

            # 超时配置
            "timeout_hours": timeout_hours,
            "timeout_seconds": timeout_seconds,
            "timeout_action": timeout_action,
            "expires_at": expires_at,

            # 输出变量映射
            "output_variables": output_variables,
            "output_mapping": output_mapping,

            # 兼容旧版
            "human_prompt": input_display or f"{title}: {description}",
            "timeout": timeout_seconds,
            "output_key": output_key,

            # 上下文信息
            "user_id": user_id,
            "execution_id": execution_id,
        }

        # 结束 Span（暂停状态）
        if span:
            end_span(span, output_data={"status": "paused"}, metadata={"waiting_for": "human_input"})

        # 返回暂停状态（LangGraph 会在此中断）
        return NodeResult(
            success=True,
            output=output,
        )

    def process_human_response(
        self,
        state: Dict[str, Any],
        selected_action: str,
        user_inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理用户的人工响应

        Args:
            state: 当前工作流状态
            selected_action: 用户选择的动作（如 "approve" 或 "reject"）
            user_inputs: 用户输入的字段值

        Returns:
            处理后的输出数据
        """
        output = {}

        # 记录选择的动作
        output["selected_action"] = selected_action

        # 记录用户输入
        output["user_inputs"] = user_inputs

        # 处理输出变量映射
        output_variables = self.config.get("output_variables", [])
        for var in output_variables:
            var_name = var.get("name", "")
            var_source = var.get("source", "")
            var_default = var.get("default")

            if var_name:
                if var_source == "selected_action":
                    output[var_name] = selected_action
                elif var_source == "user_inputs":
                    # 从用户输入中获取对应字段
                    field_name = var.get("field", var_name)
                    output[var_name] = user_inputs.get(field_name, var_default)
                elif var_source and var_source in user_inputs:
                    output[var_name] = user_inputs[var_source]
                elif var_default is not None:
                    output[var_name] = var_default

        # 兼容旧版 output_key
        output_key = self.config.get("output_key", "human_input")
        if output_key and output_key not in output:
            output[output_key] = user_inputs.get("comment", "")

        return output

    def validate_action(self, selected_action: str) -> bool:
        """验证用户选择的动作是否有效

        Args:
            selected_action: 用户选择的动作

        Returns:
            动作是否有效
        """
        action_options = self.config.get("action_options", DEFAULT_ACTION_OPTIONS)
        valid_actions = [opt.get("value") for opt in action_options if opt.get("value")]
        return selected_action in valid_actions

    def validate_inputs(self, user_inputs: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证用户输入是否满足配置要求

        Args:
            user_inputs: 用户输入的字段值

        Returns:
            (是否验证通过, 错误消息列表)
        """
        errors = []
        input_fields = self.config.get("input_fields", DEFAULT_INPUT_FIELDS)

        for field in input_fields:
            field_name = field.get("name", "")
            field_label = field.get("label", field_name)
            required = field.get("required", False)
            field_type = field.get("type", "text")

            if required and field_name not in user_inputs:
                errors.append(f"字段 '{field_label}' 是必填项")
            elif field_name in user_inputs:
                value = user_inputs[field_name]

                # 类型验证
                if field_type == "text" and not isinstance(value, str):
                    errors.append(f"字段 '{field_label}' 必须是文本类型")
                elif field_type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"字段 '{field_label}' 必须是数字类型")
                elif field_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"字段 '{field_label}' 必须是布尔类型")
                elif field_type == "array" and not isinstance(value, list):
                    errors.append(f"字段 '{field_label}' 必须是数组类型")

        return len(errors) == 0, errors

    def get_timeout_action_output(self) -> Dict[str, Any]:
        """获取超时后的默认动作输出

        Returns:
            超时动作的输出数据
        """
        timeout_action = self.config.get("timeout_action", "reject")

        return {
            "selected_action": timeout_action,
            "user_inputs": {},
            "is_timeout": True,
            "timeout_message": f"审批超时，自动执行默认动作: {timeout_action}",
        }