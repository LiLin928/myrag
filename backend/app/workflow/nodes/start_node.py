"""开始节点

支持输入变量定义和验证
"""

from typing import Dict, Any, List, Optional
from app.workflow.nodes.base_node import BaseNode, NodeResult


class StartNode(BaseNode):
    """开始节点

    配置示例:
    {
        "input_variables": [
            {"name": "query", "type": "string", "required": true, "description": "用户查询"},
            {"name": "context", "type": "string", "required": false, "description": "上下文信息"}
        ]
    }
    """

    node_type = "start"

    async def execute(self, state: Dict[str, Any]) -> NodeResult:
        """初始化工作流变量并验证输入

        Args:
            state: 工作流状态，包含用户传入的 inputs

        Returns:
            NodeResult 包含验证后的变量和输入 schema
        """
        input_variables = self.config.get("input_variables", [])
        user_inputs = state.get("inputs", {})

        # 验证必填变量
        missing_required = self._validate_required_variables(input_variables, user_inputs)
        if missing_required:
            return NodeResult(
                success=False,
                output={},
                error=f"缺少必填输入变量: {', '.join(missing_required)}"
            )

        # 类型验证
        type_errors = self._validate_variable_types(input_variables, user_inputs)
        if type_errors:
            return NodeResult(
                success=False,
                output={},
                error=f"输入变量类型错误: {'; '.join(type_errors)}"
            )

        # 合并用户输入和默认值
        variables = self._merge_inputs_with_defaults(input_variables, user_inputs)

        # 生成输入 schema
        input_schema = self._generate_input_schema(input_variables)

        return NodeResult(
            success=True,
            output={
                "variables": variables,
                "input_schema": input_schema,
            },
        )

    def _validate_required_variables(
        self,
        input_variables: List[Dict[str, Any]],
        user_inputs: Dict[str, Any]
    ) -> List[str]:
        """验证必填变量是否存在

        Args:
            input_variables: 输入变量定义列表
            user_inputs: 用户传入的输入

        Returns:
            缺失的必填变量名称列表
        """
        missing = []
        for var in input_variables:
            name = var.get("name")
            required = var.get("required", False)
            if required and name not in user_inputs:
                missing.append(name)
        return missing

    def _validate_variable_types(
        self,
        input_variables: List[Dict[str, Any]],
        user_inputs: Dict[str, Any]
    ) -> List[str]:
        """验证变量类型

        Args:
            input_variables: 输入变量定义列表
            user_inputs: 用户传入的输入

        Returns:
            类型错误信息列表
        """
        errors = []
        type_mapping = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        for var in input_variables:
            name = var.get("name")
            expected_type = var.get("type", "string")

            if name not in user_inputs:
                continue

            value = user_inputs[name]
            if value is None:
                continue

            python_type = type_mapping.get(expected_type)
            if python_type and not isinstance(value, python_type):
                # 特殊处理: 允许整数作为 number 类型
                if expected_type == "number" and isinstance(value, int):
                    continue
                errors.append(
                    f"'{name}' 应为 {expected_type} 类型，实际为 {type(value).__name__}"
                )

        return errors

    def _merge_inputs_with_defaults(
        self,
        input_variables: List[Dict[str, Any]],
        user_inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """合并用户输入和默认值

        Args:
            input_variables: 输入变量定义列表
            user_inputs: 用户传入的输入

        Returns:
            合并后的变量字典
        """
        result = {}

        for var in input_variables:
            name = var.get("name")
            default = var.get("default")

            if name in user_inputs:
                result[name] = user_inputs[name]
            elif default is not None:
                result[name] = default

        # 包含额外的用户输入（未在 schema 中定义的）
        for key, value in user_inputs.items():
            if key not in result:
                result[key] = value

        return result

    def _generate_input_schema(
        self,
        input_variables: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成输入 schema

        Args:
            input_variables: 输入变量定义列表

        Returns:
            JSON Schema 格式的输入定义
        """
        properties = {}
        required = []

        for var in input_variables:
            name = var.get("name")
            var_type = var.get("type", "string")
            description = var.get("description", "")
            default = var.get("default")
            is_required = var.get("required", False)

            prop = {
                "type": var_type,
                "description": description,
            }
            if default is not None:
                prop["default"] = default

            properties[name] = prop

            if is_required:
                required.append(name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }