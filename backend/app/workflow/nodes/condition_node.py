"""条件分支节点

根据条件表达式路由到不同节点
"""

from typing import Dict, Any, List
import logging

from app.workflow.nodes.base_node import BaseNode, NodeResult
from app.workflow.langfuse_tracker import create_span, end_span
from app.config import get_settings

logger = logging.getLogger(__name__)


class ConditionNode(BaseNode):
    """条件分支节点"""

    node_type = "condition"

    async def execute(self, state: Dict[str, Any]) -> NodeResult:
        """执行条件判断

        Args:
            state: 工作流状态

        Returns:
            NodeResult（包含 next_node）

        Config formats supported:
            New format (conditions list):
                conditions: [
                    {"expression": "${score} > 0.8", "target_node": "branch_a"},
                    {"expression": "${score} > 0.5", "target_node": "branch_b"},
                    {"expression": "default", "target_node": "fallback"}
                ]

            Old format (expression + branches):
                expression: "score > 0.8"
                branches: {"true": "node_id", "false": "node_id"}
                default: "fallback_node_id"
        """
        settings = get_settings()

        # 创建 Span（如果启用）
        span = None
        if settings.langfuse_available:
            conditions = self.config.get("conditions", [])
            span = create_span(
                trace_id=state.get("execution_id"),
                node_type=self.node_type,
                node_name=self.node_id,
                input_data={"conditions_count": len(conditions)},
                metadata={"conditions": conditions[:3] if conditions else None},
            )

        # Check for new conditions list format first
        conditions = self.config.get("conditions", [])

        if conditions:
            result = await self._execute_conditions_list(conditions, state)
        else:
            # Fall back to old format for backward compatibility
            result = await self._execute_legacy_format(state)

        # 结束 Span
        if span:
            end_span(span, output_data={"matched_condition": result.output.get("matched_condition"), "next_node": result.next_node})

        return result

    async def _execute_conditions_list(
        self, conditions: List[Dict[str, Any]], state: Dict[str, Any]
    ) -> NodeResult:
        """Execute using new conditions list format

        Args:
            conditions: List of condition configs with expression and target_node
            state: Workflow state

        Returns:
            NodeResult with matched condition
        """
        default_node = None
        matched_condition = None
        next_node = None

        for condition in conditions:
            expression = condition.get("expression", "")
            target_node = condition.get("target_node")

            # Handle default case
            if expression.lower() == "default" or expression == "":
                default_node = target_node
                continue

            # Evaluate the condition
            try:
                result = self._evaluate_expression(expression, state)
                if result:
                    next_node = target_node
                    matched_condition = expression
                    break
            except Exception as e:
                # Log error but continue to next condition
                continue

        # Use default if no condition matched
        if next_node is None:
            next_node = default_node
            if default_node is not None:
                matched_condition = "default"

        return NodeResult(
            success=True,
            output={
                "condition_result": matched_condition is not None,
                "matched_condition": matched_condition,
            },
            next_node=next_node,
        )

    async def _execute_legacy_format(self, state: Dict[str, Any]) -> NodeResult:
        """Execute using legacy expression/branches format

        Args:
            state: Workflow state

        Returns:
            NodeResult
        """
        # 获取配置
        expression = self.config.get("expression", "")
        branches = self.config.get("branches", {})  # {"true": "node_id", "false": "node_id"}
        default_branch = self.config.get("default", None)

        # 评估表达式
        try:
            result = self._evaluate_expression(expression, state)

            # 获取下一个节点
            next_node = None
            matched_condition = None
            if result and "true" in branches:
                next_node = branches["true"]
                matched_condition = "true"
            elif not result and "false" in branches:
                next_node = branches["false"]
                matched_condition = "false"
            else:
                # 检查其他分支
                for branch_name, node_id in branches.items():
                    if branch_name not in ["true", "false"]:
                        # 评估分支条件
                        if self._evaluate_expression(branch_name, state):
                            next_node = node_id
                            matched_condition = branch_name
                            break
                if next_node is None:
                    next_node = default_branch
                    if default_branch is not None:
                        matched_condition = "default"

            return NodeResult(
                success=True,
                output={
                    "condition_result": result,
                    "matched_condition": matched_condition,
                },
                next_node=next_node,
            )

        except Exception as e:
            return NodeResult(
                success=False,
                output={},
                error=str(e),
                next_node=default_branch,
            )

    def _evaluate_expression(self, expression: str, state: Dict[str, Any]) -> bool:
        """评估表达式

        Args:
            expression: 条件表达式（如 "score > 0.8"）
            state: 工作流状态

        Returns:
            条件结果
        """
        import re

        # 替换变量
        def replace_var(match):
            key = match.group(1)
            value = self.get_input_variable(state, key)
            if isinstance(value, str):
                return f"'{value}'"
            return str(value) if value is not None else "None"

        rendered = re.sub(r"\{\{(\w+)\}\}", replace_var, expression)

        # 安全评估（仅支持简单表达式）
        # 使用 eval 但限制可用函数
        allowed_names = {"True": True, "False": False, "None": None}
        try:
            result = eval(rendered, {"__builtins__": {}}, allowed_names)
            return bool(result)
        except:
            return False