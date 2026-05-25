"""Code 执行节点

在 OpenSandbox 沙箱中执行 Python 代码
"""

from typing import Dict, Any, List, Optional
import json
import logging

from app.workflow.nodes.base_node import BaseNode, NodeResult
from app.workflow.sandbox.code_executor import get_code_executor
from app.workflow.langfuse_tracker import create_span, end_span
from app.config import get_settings

logger = logging.getLogger(__name__)


class CodeNode(BaseNode):
    """代码执行节点"""

    node_type = "code"

    # 默认沙箱配置
    DEFAULT_MEMORY_LIMIT_MB = 256
    DEFAULT_TIMEOUT_SECONDS = 30
    DEFAULT_ALLOWED_MODULES = [
        "json",
        "math",
        "datetime",
        "collections",
        "itertools",
        "functools",
        "re",
        "string",
        "random",
        "typing",
    ]

    async def execute(self, state: Dict[str, Any]) -> NodeResult:
        """执行代码

        Args:
            state: 工作流状态

        Returns:
            NodeResult
        """
        settings = get_settings()

        # 获取沙箱配置
        sandbox_config = self._get_sandbox_config()

        # 解析输入变量
        input_variables = self._resolve_input_variables(state)

        # 获取代码模板和包
        code_template = self.config.get("code", "")
        packages = self.config.get("packages", [])

        # 渲染代码（替换变量）
        code = self._render_code(code_template, state)

        # 如果有输入变量，注入到代码中
        if input_variables:
            code = self._inject_input_variables(code, input_variables)

        # 创建 Span（如果启用）
        span = None
        if settings.langfuse_available:
            span = create_span(
                trace_id=state.get("execution_id"),
                node_type=self.node_type,
                node_name=self.node_id,
                input_data={"packages": packages, "input_vars": list(input_variables.keys())},
                metadata={"timeout": sandbox_config["timeout_seconds"]},
            )

        # 验证代码语法
        code_executor = get_code_executor()
        validation = await code_executor.validate_code(code)
        if not validation["valid"]:
            if span:
                end_span(span, output_data={}, metadata={"error": validation["error"]})
            return NodeResult(
                success=False,
                output={},
                error=f"Code syntax error: {validation['error']}",
            )

        # 执行代码
        try:
            result = await code_executor.execute(
                code=code,
                timeout=sandbox_config["timeout_seconds"],
                packages=packages,
            )

            if result["success"]:
                # 处理输出变量映射
                output = result.get("output")
                output_variables = self._map_output_variables(output)

                # 结束 Span
                if span:
                    end_span(span, output_data={"success": True})

                return NodeResult(
                    success=True,
                    output=output_variables,
                )
            else:
                if span:
                    end_span(span, output_data={}, metadata={"error": result.get("error")})
                return NodeResult(
                    success=False,
                    output={},
                    error=result.get("error", "Unknown execution error"),
                )

        except Exception as e:
            logger.error(f"Code node {self.node_id} execution failed: {e}")
            if span:
                end_span(span, output_data={}, metadata={"error": str(e)})
            return NodeResult(
                success=False,
                output={},
                error=str(e),
            )

    def _get_sandbox_config(self) -> Dict[str, Any]:
        """获取沙箱配置

        合并默认配置和用户配置

        Returns:
            沙箱配置字典
        """
        # 获取用户配置
        user_config = self.config.get("sandbox_config", {})

        # 合并配置
        return {
            "memory_limit_mb": user_config.get(
                "memory_limit_mb", self.DEFAULT_MEMORY_LIMIT_MB
            ),
            "timeout_seconds": user_config.get(
                "timeout_seconds", self.DEFAULT_TIMEOUT_SECONDS
            ),
            "allowed_modules": user_config.get(
                "allowed_modules", self.DEFAULT_ALLOWED_MODULES
            ),
        }

    def _resolve_input_variables(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """解析输入变量

        将 input_variables 配置映射到实际值

        input_variables 格式:
        [
            {"name": "input_data", "source": "node_1.output.result"},
            {"name": "config", "source": "variables.config"},
        ]

        Args:
            state: 工作流状态

        Returns:
            解析后的输入变量字典
        """
        input_variables_config = self.config.get("input_variables", [])
        if not input_variables_config:
            return {}

        resolved = {}
        for var_config in input_variables_config:
            var_name = var_config.get("name")
            source = var_config.get("source")

            if not var_name or not source:
                logger.warning(
                    f"Invalid input variable config in node {self.node_id}: {var_config}"
                )
                continue

            # 解析源路径
            value = self._resolve_source_path(source, state)
            resolved[var_name] = value

        return resolved

    def _resolve_source_path(self, source: str, state: Dict[str, Any]) -> Any:
        """解析源路径

        支持格式:
        - "variables.key" - 从全局变量获取
        - "node_id.output.key" - 从节点输出获取
        - "node_id.output" - 获取整个节点输出

        Args:
            source: 源路径
            state: 工作流状态

        Returns:
            解析后的值
        """
        parts = source.split(".")
        if len(parts) < 2:
            logger.warning(f"Invalid source path: {source}")
            return None

        source_type = parts[0]

        if source_type == "variables":
            # 从全局变量获取
            key = ".".join(parts[1:])
            return self._extract_by_path(state.get("variables", {}), key)

        elif source_type == "node_id":
            # 从节点输出获取（格式: node_id.output.key）
            if len(parts) < 3:
                logger.warning(f"Invalid node output path: {source}")
                return None

            node_id = parts[1]
            rest_path = ".".join(parts[2:])

            node_output = self.get_previous_output(state, node_id)
            if node_output is None:
                logger.warning(f"Node output not found: {node_id}")
                return None

            return self._extract_by_path(node_output, rest_path)

        else:
            logger.warning(f"Unknown source type: {source_type}")
            return None

    def _inject_input_variables(self, code: str, input_variables: Dict[str, Any]) -> str:
        """注入输入变量到代码

        在代码开头添加变量定义

        Args:
            code: 原始代码
            input_variables: 输入变量字典

        Returns:
            注入变量后的代码
        """
        # 生成变量注入代码
        inject_lines = ["import json", ""]
        for var_name, var_value in input_variables.items():
            # 将值转换为 JSON 安全格式
            value_json = json.dumps(var_value)
            inject_lines.append(f"{var_name} = json.loads('{value_json}')")

        inject_lines.append("")
        inject_lines.append("# User code starts here")

        # 组合代码
        inject_code = "\n".join(inject_lines)
        return f"{inject_code}\n{code}"

    def _map_output_variables(self, output: Any) -> Dict[str, Any]:
        """映射输出变量

        将代码执行结果映射到指定的输出变量名

        output_variables 格式:
        [
            {"source": "result", "name": "final_output"},
            {"source": "items", "name": "processed_items"},
        ]

        Args:
            output: 代码执行结果

        Returns:
            映射后的输出字典
        """
        output_variables_config = self.config.get("output_variables", [])

        if not output_variables_config:
            # 没有配置输出变量映射，使用默认输出
            return {"result": output}

        result = {}

        # 如果输出是字典，可以直接提取
        output_dict = output if isinstance(output, dict) else {"value": output}

        for var_config in output_variables_config:
            source = var_config.get("source")
            name = var_config.get("name")

            if not source or not name:
                logger.warning(
                    f"Invalid output variable config in node {self.node_id}: {var_config}"
                )
                continue

            # 从输出中提取值
            value = self._extract_by_path(output_dict, source)
            result[name] = value

        return result

    def _render_code(self, template: str, state: Dict[str, Any]) -> str:
        """渲染代码模板

        替换 {{variable}} 格式的变量

        Args:
            template: 代码模板
            state: 工作流状态

        Returns:
            渲染后的代码
        """
        import re

        def replace_var(match):
            key = match.group(1)
            value = self.get_input_variable(state, key)
            # 如果是复杂对象，转换为 JSON
            if isinstance(value, (dict, list)):
                return json.dumps(value)
            return str(value) if value is not None else "None"

        return re.sub(r"\{\{(\w+)\}\}", replace_var, template)

    def get_sandbox_config_summary(self) -> Dict[str, Any]:
        """获取沙箱配置摘要（用于调试和日志）

        Returns:
            沙箱配置摘要
        """
        config = self._get_sandbox_config()
        return {
            "memory_limit_mb": config["memory_limit_mb"],
            "timeout_seconds": config["timeout_seconds"],
            "allowed_modules_count": len(config["allowed_modules"]),
        }