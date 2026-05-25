"""节点基类

所有工作流节点继承此基类，实现 execute 方法
"""

from typing import Dict, Any, Optional, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class ErrorHandlingStrategy(str, Enum):
    """错误处理策略"""

    ABORT = "abort"  # 终止工作流
    SKIP = "skip"  # 跳过当前节点
    FALLBACK = "fallback"  # 使用备用值
    RETRY = "retry"  # 重试（已弃用，使用 retry_count 代替）


@dataclass
class NodeResult:
    """节点执行结果"""

    success: bool
    output: Dict[str, Any]
    error: Optional[str] = None
    next_node: Optional[str] = None  # 下一个节点 ID（条件节点使用）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "next_node": self.next_node,
        }


class BaseNode(ABC):
    """节点基类"""

    node_type: str = "base"

    def __init__(self, node_id: str, config: Dict[str, Any]):
        """初始化节点

        Args:
            node_id: 节点唯一 ID
            config: 节点配置
        """
        self.node_id = node_id
        self.config = config

    @abstractmethod
    async def execute(self, state: Dict[str, Any]) -> NodeResult:
        """执行节点逻辑

        Args:
            state: 工作流状态（包含 variables、node_outputs 等）

        Returns:
            NodeResult
        """
        pass

    def get_input_variable(self, state: Dict[str, Any], key: str) -> Any:
        """获取输入变量

        Args:
            state: 工作流状态
            key: 变量键

        Returns:
            变量值
        """
        # 从 variables 中获取
        variables = state.get("variables", {})
        return variables.get(key)

    def set_output_variable(self, state: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]:
        """设置输出变量

        Args:
            state: 工作流状态
            key: 变量键
            value: 变量值

        Returns:
            更新后的状态
        """
        variables = state.get("variables", {})
        variables[key] = value
        return {"variables": variables}

    def get_previous_output(self, state: Dict[str, Any], node_id: str) -> Optional[Dict[str, Any]]:
        """获取上一个节点的输出

        Args:
            state: 工作流状态
            node_id: 节点 ID

        Returns:
            节点输出
        """
        node_outputs = state.get("node_outputs", {})
        return node_outputs.get(node_id)

    def validate_config(self, required_keys: list) -> bool:
        """验证配置是否完整

        Args:
            required_keys: 必需的配置键

        Returns:
            是否有效
        """
        for key in required_keys:
            if key not in self.config:
                return False
        return True

    def render_template(self, template: str, state: Dict[str, Any]) -> str:
        """渲染模板（替换 {{variable}}）

        Args:
            template: 模板字符串
            state: 工作流状态

        Returns:
            渲染后的字符串
        """
        import re

        def replace_var(match):
            key = match.group(1)
            value = self.get_input_variable(state, key)
            return str(value) if value is not None else ""

        return re.sub(r"\{\{(\w+)\}\}", replace_var, template)

    # ========== 通用配置属性 ==========

    def get_timeout(self) -> int:
        """获取节点执行超时时间（秒）

        Returns:
            超时时间，默认 300 秒
        """
        return self.config.get("timeout", 300)

    def get_retry_count(self) -> int:
        """获取失败重试次数

        Returns:
            重试次数，默认 0
        """
        return self.config.get("retry_count", 0)

    def get_retry_delay(self) -> float:
        """获取重试延迟时间（秒）

        Returns:
            重试延迟时间，默认 1.0 秒
        """
        return self.config.get("retry_delay", 1.0)

    def get_error_handling(self) -> ErrorHandlingStrategy:
        """获取错误处理策略

        Returns:
            错误处理策略，默认 abort
        """
        strategy = self.config.get("error_handling", "abort")
        try:
            return ErrorHandlingStrategy(strategy)
        except ValueError:
            logger.warning(f"Invalid error_handling strategy: {strategy}, defaulting to abort")
            return ErrorHandlingStrategy.ABORT

    def get_name(self) -> str:
        """获取节点显示名称

        Returns:
            节点名称，默认使用 node_id
        """
        return self.config.get("name", self.node_id)

    def get_description(self) -> str:
        """获取节点描述

        Returns:
            节点描述，默认为空字符串
        """
        return self.config.get("description", "")

    # ========== 高级执行方法 ==========

    async def execute_with_retry(
        self,
        state: Dict[str, Any],
        resolver: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    ) -> NodeResult:
        """带重试和变量解析的执行方法

        Args:
            state: 工作流状态
            resolver: 变量解析器函数，用于解析复杂变量引用

        Returns:
            NodeResult
        """
        retry_count = self.get_retry_count()
        retry_delay = self.get_retry_delay()
        last_error: Optional[str] = None

        # If resolver is provided, resolve variable references in config
        original_config = None
        if resolver:
            resolved_config = resolver.resolve_dict(self.config)
            # Store original config for restoration after execution
            original_config = self.config
            self.config = resolved_config

        for attempt in range(retry_count + 1):
            try:
                # 执行节点
                result = await self.execute(state)

                # 如果成功，处理输出变量映射
                if result.success:
                    output_mappings = self.config.get("output_mappings", {})
                    if output_mappings:
                        result.output = self.map_output_variables(
                            result.output, output_mappings
                        )

                # Restore original config after execution
                if original_config is not None:
                    self.config = original_config

                return result

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Node {self.node_id} execution failed (attempt {attempt + 1}/{retry_count + 1}): {last_error}"
                )

                # 如果还有重试机会，等待后重试
                if attempt < retry_count:
                    await asyncio.sleep(retry_delay)
                else:
                    # Restore original config after execution
                    if original_config is not None:
                        self.config = original_config
                    # 所有重试都失败，根据错误处理策略返回结果
                    return self._handle_execution_error(state, last_error)

        # 不应该到达这里，但作为安全措施
        # Restore original config after execution
        if original_config is not None:
            self.config = original_config
        return NodeResult(success=False, output={}, error=last_error)

    def _handle_execution_error(
        self, state: Dict[str, Any], error: str
    ) -> NodeResult:
        """根据错误处理策略处理执行错误

        Args:
            state: 工作流状态
            error: 错误信息

        Returns:
            NodeResult
        """
        strategy = self.get_error_handling()

        if strategy == ErrorHandlingStrategy.ABORT:
            return NodeResult(success=False, output={}, error=error)

        elif strategy == ErrorHandlingStrategy.SKIP:
            logger.info(f"Node {self.node_id} skipped due to error: {error}")
            return NodeResult(success=True, output={"skipped": True, "error": error})

        elif strategy == ErrorHandlingStrategy.FALLBACK:
            fallback_output = self.config.get("fallback_output", {})
            logger.info(f"Node {self.node_id} using fallback output: {fallback_output}")
            return NodeResult(success=True, output=fallback_output)

        else:
            return NodeResult(success=False, output={}, error=error)

    def map_output_variables(
        self, output: Dict[str, Any], mappings: Dict[str, str]
    ) -> Dict[str, Any]:
        """映射输出变量到自定义变量名

        Args:
            output: 原始输出
            mappings: 变量映射 {原变量名: 新变量名}

        Returns:
            映射后的输出
        """
        mapped_output = {}

        for key, value in output.items():
            if key in mappings:
                new_key = mappings[key]
                mapped_output[new_key] = value
            else:
                mapped_output[key] = value

        return mapped_output

    def _extract_by_path(self, data: Dict[str, Any], path: str) -> Any:
        """通过路径提取值

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