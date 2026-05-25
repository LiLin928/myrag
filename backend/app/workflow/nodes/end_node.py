"""结束节点

支持输出变量定义和映射
"""

from typing import Dict, Any, List
import re
from app.workflow.nodes.base_node import BaseNode, NodeResult


class EndNode(BaseNode):
    """结束节点

    配置示例:
    {
        "output_variables": [
            {"name": "response", "variable": "${llm_response}"},
            {"name": "sources", "variable": "${retrieval_result.documents}"}
        ]
    }
    """

    node_type = "end"

    async def execute(self, state: Dict[str, Any]) -> NodeResult:
        """收集并输出最终变量

        Args:
            state: 工作流状态，包含所有执行过程中产生的变量

        Returns:
            NodeResult 包含最终输出的映射变量
        """
        output_variables = self.config.get("output_variables", [])

        # 解析并收集输出变量
        final_output = self._resolve_output_variables(output_variables, state)

        return NodeResult(
            success=True,
            output={
                "status": "completed",
                "final_output": final_output,
            },
        )

    def _resolve_output_variables(
        self,
        output_variables: List[Dict[str, Any]],
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """解析输出变量引用

        支持变量引用语法:
        - ${variable_name} - 从 state.variables 中获取
        - ${node_id.output_key} - 从节点输出中获取
        - ${node_id.output_key.nested_path} - 从节点输出的嵌套路径获取

        Args:
            output_variables: 输出变量定义列表
            state: 工作流状态

        Returns:
            解析后的输出变量字典
        """
        result = {}

        for var in output_variables:
            name = var.get("name")
            variable_ref = var.get("variable", "")
            default = var.get("default")

            if not name:
                continue

            # 解析变量引用
            value = self._resolve_variable_reference(variable_ref, state)

            # 如果解析失败，使用默认值
            if value is None and default is not None:
                value = default

            result[name] = value

        return result

    def _resolve_variable_reference(
        self,
        reference: str,
        state: Dict[str, Any]
    ) -> Any:
        """解析变量引用

        支持格式:
        - ${var_name} - 从 variables 中获取
        - ${node_id.output_key} - 从节点输出中获取
        - ${node_id.output_key.path.to.value} - 嵌套路径

        Args:
            reference: 变量引用字符串
            state: 工作流状态

        Returns:
            解析后的值，如果解析失败返回 None
        """
        if not reference:
            return None

        # 提取 ${...} 中的内容
        match = re.match(r"\$\{(.+)\}", reference)
        if not match:
            # 不是变量引用，直接返回原值
            return reference

        ref_path = match.group(1)
        parts = ref_path.split(".")

        # 第一部分决定来源
        first_part = parts[0]

        # 尝试从 variables 中获取
        variables = state.get("variables", {})
        if first_part in variables:
            if len(parts) == 1:
                return variables[first_part]
            else:
                # 嵌套路径
                return self._extract_nested_path(
                    variables[first_part],
                    ".".join(parts[1:])
                )

        # 尝试从 node_outputs 中获取
        node_outputs = state.get("node_outputs", {})
        if first_part in node_outputs:
            node_output = node_outputs[first_part]
            if len(parts) == 1:
                return node_output
            else:
                # 嵌套路径: node_id.output_key...
                return self._extract_nested_path(
                    node_output,
                    ".".join(parts[1:])
                )

        # 尝试从 inputs 中获取
        inputs = state.get("inputs", {})
        if first_part in inputs:
            if len(parts) == 1:
                return inputs[first_part]
            else:
                return self._extract_nested_path(
                    inputs[first_part],
                    ".".join(parts[1:])
                )

        return None

    def _extract_nested_path(self, data: Any, path: str) -> Any:
        """从嵌套数据中提取值

        Args:
            data: 数据对象
            path: 点号分隔的路径

        Returns:
            提取的值，如果路径不存在返回 None
        """
        if not path:
            return data

        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif hasattr(current, key):
                current = getattr(current, key)
            else:
                return None

        return current

    def _extract_by_path(self, data: Dict[str, Any], path: str) -> Any:
        """通过路径提取值（继承自基类的辅助方法）

        支持点号分隔的路径，如 "result.data.items"

        Args:
            data: 数据字典
            path: 路径字符串

        Returns:
            提取的值，如果路径不存在返回 None
        """
        if not path:
            return None

        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current