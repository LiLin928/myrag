"""循环节点

支持两种循环类型：
- array: 遍历数组元素
- condition: 条件循环（while 循环）
"""

from typing import Dict, Any, List, Optional
from app.workflow.nodes.base_node import BaseNode, NodeResult
from app.workflow.langfuse_tracker import create_span, end_span
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)


class LoopNode(BaseNode):
    """循环节点"""

    node_type = "loop"

    # ========== 配置属性方法 ==========

    def get_loop_type(self) -> str:
        """获取循环类型

        Returns:
            循环类型: "array" 或 "condition"，默认 "array"
        """
        return self.config.get("loop_type", "array")

    def get_input_array(self) -> Any:
        """获取输入数组配置

        支持两种格式：
        - 变量引用: "${variable_name}" 或 "${node_id.output_key}"
        - 直接数组: ["item1", "item2", ...]

        Returns:
            输入数组配置
        """
        return self.config.get("input_array")

    def get_loop_variable(self) -> str:
        """获取循环变量名

        Returns:
            循环变量名，默认 "item"
        """
        return self.config.get("loop_variable", "item")

    def get_loop_index_variable(self) -> str:
        """获取循环索引变量名

        Returns:
            循环索引变量名，默认 "index"
        """
        return self.config.get("loop_index_variable", "index")

    def get_max_iterations(self) -> int:
        """获取最大迭代次数

        Returns:
            最大迭代次数，默认 100（防止无限循环）
        """
        return self.config.get("max_iterations", 100)

    def get_output_type(self) -> str:
        """获取输出类型

        Returns:
            输出类型:
            - "collect": 收集所有迭代结果为数组
            - "last": 只返回最后一次迭代结果
            - "custom": 自定义输出变量映射
        """
        return self.config.get("output_type", "collect")

    def get_output_key(self) -> str:
        """获取输出变量键名

        Returns:
            输出变量键名，默认 "loop_results"
        """
        return self.config.get("output_key", "loop_results")

    def get_output_variables(self) -> Dict[str, str]:
        """获取输出变量映射

        Returns:
            输出变量映射 {原变量名: 新变量名}
        """
        return self.config.get("output_variables", {})

    def get_sub_nodes(self) -> List[Dict[str, Any]]:
        """获取子节点定义列表

        Returns:
            子节点定义列表
        """
        return self.config.get("sub_nodes", [])

    def get_condition(self) -> str:
        """获取条件表达式（仅 condition 类型使用）

        Returns:
            条件表达式
        """
        return self.config.get("condition", "")

    # ========== 变量解析方法 ==========

    def _resolve_array_reference(self, state: Dict[str, Any]) -> Optional[List]:
        """解析数组引用

        支持格式：
        - 变量引用: "${variable_name}" 或 "${node_id.output_key}"
        - 直接数组: ["item1", "item2", ...]

        Args:
            state: 工作流状态

        Returns:
            解析后的数组，解析失败返回 None
        """
        input_array = self.get_input_array()

        if input_array is None:
            return None

        # 如果已经是数组，直接返回
        if isinstance(input_array, list):
            return input_array

        # 如果是字符串，尝试解析变量引用
        if isinstance(input_array, str):
            # 检查是否是变量引用格式 ${...}
            import re
            match = re.match(r'\$\{([^}]+)\}', input_array)
            if match:
                var_path = match.group(1)
                value = self._get_variable_by_path(state, var_path)
                if isinstance(value, list):
                    return value
                else:
                    logger.warning(f"Variable {var_path} is not a list: {type(value)}")
                    return None

        logger.warning(f"Invalid input_array format: {input_array}")
        return None

    def _get_variable_by_path(self, state: Dict[str, Any], path: str) -> Any:
        """通过路径获取变量值

        支持格式：
        - "variable_name": 从 variables 中获取
        - "node_id.output_key": 从节点输出中获取
        - "node_id.output_key[0].field": 支持数组索引和嵌套字段

        Args:
            state: 工作流状态
            path: 变量路径

        Returns:
            变量值
        """
        # 解析路径
        parts = self._parse_path(path)

        if not parts:
            return None

        first_part = parts[0]

        # 检查是否是节点输出引用 (格式: node_id.output_key)
        if '.' in path or '[' in path:
            node_outputs = state.get("node_outputs", {})
            if first_part in node_outputs:
                return self._follow_path(node_outputs[first_part], parts[1:])

        # 从 variables 中获取
        variables = state.get("variables", {})
        if first_part in variables:
            return self._follow_path(variables[first_part], parts[1:])

        return None

    def _parse_path(self, path: str) -> List[str]:
        """解析变量路径

        Args:
            path: 变量路径字符串

        Returns:
            路径部分列表
        """
        parts = []
        current = ""
        i = 0

        while i < len(path):
            char = path[i]

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

    # ========== 条件评估方法 ==========

    def _evaluate_condition(self, expression: str, state: Dict[str, Any]) -> bool:
        """评估条件表达式

        Args:
            expression: 条件表达式
            state: 工作流状态

        Returns:
            条件结果
        """
        import re

        # 替换变量引用 ${variable_name}
        def replace_var(match):
            key = match.group(1)
            value = self._get_variable_by_path(state, key)
            if isinstance(value, str):
                return f"'{value}'"
            return str(value) if value is not None else "None"

        rendered = re.sub(r'\$\{([^}]+)\}', replace_var, expression)

        # 安全评估（仅支持简单表达式）
        allowed_names = {"True": True, "False": False, "None": None}
        try:
            result = eval(rendered, {"__builtins__": {}}, allowed_names)
            return bool(result)
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {e}")
            return False

    # ========== 子节点执行方法 ==========

    async def _execute_sub_nodes(
        self,
        state: Dict[str, Any],
        iteration_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行子节点序列

        Args:
            state: 工作流状态
            iteration_state: 当前迭代的变量状态

        Returns:
            子节点执行结果
        """
        # 延迟导入避免循环依赖
        from app.workflow.engine.node_router import create_node

        sub_nodes = self.get_sub_nodes()

        if not sub_nodes:
            return {}

        # 合并迭代状态到工作流状态
        current_state = {
            **state,
            "variables": {**state.get("variables", {}), **iteration_state},
        }

        # 存储每个子节点的输出
        iteration_outputs = {}

        for node_def in sub_nodes:
            node_id = node_def.get("id", f"sub_{len(iteration_outputs)}")
            node_type = node_def.get("type", "start")
            node_config = node_def.get("data", {}).get("config", {})

            try:
                # 创建并执行节点
                node = create_node(node_id, node_type, node_config)
                result = await node.execute(current_state)

                # 更新状态
                iteration_outputs[node_id] = result.output
                current_state["node_outputs"] = {
                    **current_state.get("node_outputs", {}),
                    node_id: result.output,
                }

                if not result.success:
                    logger.warning(f"Sub-node {node_id} failed: {result.error}")
                    # 继续执行或根据错误处理策略处理
                    # 这里选择继续执行，但记录错误
                    iteration_outputs[f"{node_id}_error"] = result.error

            except Exception as e:
                logger.error(f"Failed to execute sub-node {node_id}: {e}")
                iteration_outputs[f"{node_id}_error"] = str(e)

        return iteration_outputs

    # ========== 主执行方法 ==========

    async def execute(self, state: Dict[str, Any]) -> NodeResult:
        """执行循环逻辑

        Args:
            state: 工作流状态

        Returns:
            NodeResult
        """
        settings = get_settings()

        loop_type = self.get_loop_type()
        max_iterations = self.get_max_iterations()
        output_key = self.get_output_key()
        output_type = self.get_output_type()
        output_variables = self.get_output_variables()

        # 创建 Span（如果启用）
        span = None
        if settings.langfuse_available:
            input_array = self._resolve_array_reference(state) if loop_type == "array" else None
            span = create_span(
                trace_id=state.get("execution_id"),
                node_type=self.node_type,
                node_name=self.node_id,
                input_data={"loop_type": loop_type, "array_length": len(input_array) if input_array else None},
                metadata={"max_iterations": max_iterations, "output_type": output_type},
            )

        results = []
        iteration_count = 0

        if loop_type == "array":
            result = await self._execute_array_loop(state)
        elif loop_type == "condition":
            result = await self._execute_condition_loop(state)
        else:
            if span:
                end_span(span, output_data={}, metadata={"error": f"Unknown loop_type: {loop_type}"})
            return NodeResult(
                success=False,
                output={},
                error=f"Unknown loop_type: {loop_type}",
            )

        # 结束 Span
        if span:
            end_span(span, output_data={"loop_count": result.output.get("loop_count", 0)}, metadata={})

        # 应用输出变量映射
        if output_variables:
            result.output = self.map_output_variables(result.output, output_variables)

        return result

    async def _execute_array_loop(self, state: Dict[str, Any]) -> NodeResult:
        """执行数组遍历循环

        Args:
            state: 工作流状态

        Returns:
            NodeResult
        """
        # 获取输入数组
        items = self._resolve_array_reference(state)

        if items is None:
            return NodeResult(
                success=False,
                output={},
                error="Failed to resolve input_array",
            )

        loop_var = self.get_loop_variable()
        index_var = self.get_loop_index_variable()
        max_iterations = self.get_max_iterations()
        output_type = self.get_output_type()
        output_key = self.get_output_key()

        results = []

        # 限制迭代次数
        items_to_process = items[:max_iterations]

        for index, item in enumerate(items_to_process):
            # 构建迭代状态
            iteration_state = {
                loop_var: item,
                index_var: index,
                "loop_index": index,
                "loop_count": len(items_to_process),
                "is_first": index == 0,
                "is_last": index == len(items_to_process) - 1,
            }

            # 执行子节点
            if self.get_sub_nodes():
                iteration_output = await self._execute_sub_nodes(state, iteration_state)
            else:
                # 无子节点，只返回迭代信息
                iteration_output = iteration_state

            results.append(iteration_output)

        # 根据输出类型处理结果
        output = self._process_output(results, output_type, output_key)

        return NodeResult(
            success=True,
            output=output,
        )

    async def _execute_condition_loop(self, state: Dict[str, Any]) -> NodeResult:
        """执行条件循环

        Args:
            state: 工作流状态

        Returns:
            NodeResult
        """
        condition = self.get_condition()
        max_iterations = self.get_max_iterations()
        output_type = self.get_output_type()
        output_key = self.get_output_key()
        loop_var = self.get_loop_variable()
        index_var = self.get_loop_index_variable()

        results = []
        iteration_count = 0

        while iteration_count < max_iterations:
            # 评估条件
            if not self._evaluate_condition(condition, state):
                break

            # 构建迭代状态
            iteration_state = {
                index_var: iteration_count,
                "loop_index": iteration_count,
                "is_first": iteration_count == 0,
            }

            # 执行子节点
            if self.get_sub_nodes():
                iteration_output = await self._execute_sub_nodes(state, iteration_state)
            else:
                iteration_output = iteration_state

            results.append(iteration_output)
            iteration_count += 1

            # 更新状态（用于下一次条件评估）
            state["variables"][f"{loop_var}_result"] = iteration_output

        # 根据输出类型处理结果
        output = self._process_output(results, output_type, output_key)

        output["iteration_count"] = iteration_count
        output["completed"] = iteration_count < max_iterations

        return NodeResult(
            success=True,
            output=output,
        )

    def _process_output(
        self,
        results: List[Dict[str, Any]],
        output_type: str,
        output_key: str,
    ) -> Dict[str, Any]:
        """处理循环输出

        Args:
            results: 所有迭代结果
            output_type: 输出类型
            output_key: 输出键名

        Returns:
            处理后的输出字典
        """
        output = {}

        if output_type == "collect":
            # 收集所有结果
            output[output_key] = results
            output["loop_count"] = len(results)
        elif output_type == "last":
            # 只返回最后一次结果
            output[output_key] = results[-1] if results else None
            output["loop_count"] = len(results)
        elif output_type == "custom":
            # 自定义输出
            output[output_key] = results
            output["loop_count"] = len(results)
            # 可通过 output_variables 进一步映射
        else:
            # 默认收集
            output[output_key] = results
            output["loop_count"] = len(results)

        return output