"""变量解析器

解析工作流中的变量引用表达式
"""

from typing import Dict, Any, Optional, List
import re
from datetime import datetime, timezone


class VariableResolver:
    """变量解析器

    支持的变量类型:
    - 输入变量: ${query}
    - 节点输出变量: ${llm_node.response}
    - 数组元素引用: ${rag_chunks[0].content}
    - 嵌套路径: ${node_output.data.items[0].name}
    - 环境变量: ${timestamp}, ${execution_id}
    """

    # 变量引用模式: ${variable_name} 或 ${node_id.output_key}
    VAR_PATTERN = re.compile(r'\$\{([^}]+)\}')

    def __init__(
        self,
        input_vars: Dict[str, Any],
        global_vars: Optional[Dict[str, Any]] = None,
        env_vars: Optional[Dict[str, Any]] = None,
    ):
        """初始化变量解析器

        Args:
            input_vars: 工作流输入变量
            global_vars: 全局共享变量
            env_vars: 系统环境变量
        """
        self.input_vars = input_vars or {}
        self.global_vars = global_vars or {}
        self.env_vars = env_vars or self._get_default_env_vars()
        self.node_outputs: Dict[str, Dict[str, Any]] = {}

    def _get_default_env_vars(self) -> Dict[str, Any]:
        """获取默认环境变量"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        }

    def add_node_output(self, node_id: str, output: Dict[str, Any]):
        """添加节点输出

        Args:
            node_id: 节点 ID
            output: 节点输出数据
        """
        self.node_outputs[node_id] = output

    def resolve(self, expression: str) -> Any:
        """解析表达式中的变量引用

        Args:
            expression: 包含变量引用的表达式

        Returns:
            解析后的值
        """
        if not isinstance(expression, str):
            return expression

        # 如果整个表达式是单个变量引用，返回实际值
        match = self.VAR_PATTERN.fullmatch(expression)
        if match:
            var_path = match.group(1)
            return self._get_variable_value(var_path)

        # 否则替换所有变量引用为字符串
        def replace_var(match):
            var_path = match.group(1)
            value = self._get_variable_value(var_path)
            if isinstance(value, (dict, list)):
                return str(value)
            return str(value) if value is not None else ""

        return self.VAR_PATTERN.sub(replace_var, expression)

    def resolve_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """解析字典中的所有变量引用

        Args:
            data: 包含变量引用的字典

        Returns:
            解析后的字典
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.resolve(value)
            elif isinstance(value, dict):
                result[key] = self.resolve_dict(value)
            elif isinstance(value, list):
                result[key] = self.resolve_list(value)
            else:
                result[key] = value
        return result

    def resolve_list(self, data: List[Any]) -> List[Any]:
        """解析列表中的所有变量引用

        Args:
            data: 包含变量引用的列表

        Returns:
            解析后的列表
        """
        result = []
        for item in data:
            if isinstance(item, str):
                result.append(self.resolve(item))
            elif isinstance(item, dict):
                result.append(self.resolve_dict(item))
            elif isinstance(item, list):
                result.append(self.resolve_list(item))
            else:
                result.append(item)
        return result

    def _get_variable_value(self, var_path: str) -> Any:
        """获取变量值

        Args:
            var_path: 变量路径（如 "query", "llm_node.response", "chunks[0].content"）

        Returns:
            变量值
        """
        # 解析路径
        parts = self._parse_path(var_path)

        if not parts:
            return None

        # 第一个的部分决定变量来源
        first_part = parts[0]

        # 检查环境变量
        if first_part in self.env_vars:
            return self._follow_path(self.env_vars, parts)

        # 检查全局变量
        if first_part in self.global_vars:
            return self._follow_path(self.global_vars, parts)

        # 检查是否是节点输出引用 (格式: node_id.output_key)
        if '.' in var_path or '[' in var_path:
            node_id = first_part
            if node_id in self.node_outputs:
                return self._follow_path(self.node_outputs[node_id], parts[1:])

        # 检查输入变量
        if first_part in self.input_vars:
            return self._follow_path(self.input_vars, parts)

        return None

    def _parse_path(self, var_path: str) -> List[str]:
        """解析变量路径

        Args:
            var_path: 变量路径字符串

        Returns:
            路径部分列表
        """
        # 分割路径: "node_id.output_key[0].field" -> ["node_id", "output_key", "[0]", "field"]
        parts = []
        current = ""
        i = 0

        while i < len(var_path):
            char = var_path[i]

            if char == '.':
                if current:
                    parts.append(current)
                    current = ""
            elif char == '[':
                if current:
                    parts.append(current)
                    current = "["
            elif char == ']':
                current += char
                parts.append(current)
                current = ""
            else:
                current += char

            i += 1

        if current:
            parts.append(current)

        return parts

    def _follow_path(self, data: Any, parts: List[str]) -> Any:
        """跟随路径获取值

        Args:
            data: 数据对象
            parts: 路径部分列表

        Returns:
            最终值
        """
        current = data

        for part in parts:
            if current is None:
                return None

            # 数组索引访问
            if part.startswith('[') and part.endswith(']'):
                try:
                    index = int(part[1:-1])
                except ValueError:
                    return None
                if isinstance(current, list) and 0 <= index < len(current):
                    current = current[index]
                else:
                    return None
            # 字典键访问
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                return None

        return current

    def get_available_variables(self) -> Dict[str, Any]:
        """获取所有可用变量

        Returns:
            分类后的变量列表
        """
        return {
            "input": list(self.input_vars.keys()),
            "global": list(self.global_vars.keys()),
            "env": list(self.env_vars.keys()),
            "node_outputs": {
                node_id: list(output.keys())
                for node_id, output in self.node_outputs.items()
            },
        }