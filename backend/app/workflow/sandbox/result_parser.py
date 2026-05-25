"""执行结果解析器

解析沙箱执行结果，处理 JSON 输出、错误信息
"""

import json
from typing import Dict, Any, Optional


class ResultParser:
    """执行结果解析器"""

    def parse(self, output: str) -> Dict[str, Any]:
        """解析执行输出

        Args:
            output: 容器执行输出

        Returns:
            解析后的结果
        """
        if not output:
            return {
                "success": False,
                "output": "",
                "error": "Empty output",
            }

        # 尝试解析 JSON
        try:
            result = json.loads(output.strip())
            return result
        except json.JSONDecodeError:
            # 非 JSON 输出，作为纯文本返回
            return {
                "success": True,
                "output": output.strip(),
                "error": None,
            }

    def parse_error(self, error_message: str) -> Dict[str, Any]:
        """解析错误信息

        Args:
            error_message: 错误消息

        Returns:
            结构化错误信息
        """
        # 常见错误类型检测
        error_types = {
            "SyntaxError": "语法错误",
            "RuntimeError": "运行时错误",
            "ImportError": "导入错误",
            "TypeError": "类型错误",
            "ValueError": "值错误",
            "TimeoutError": "超时错误",
        }

        for error_type, description in error_types.items():
            if error_type in error_message:
                return {
                    "type": error_type,
                    "description": description,
                    "message": error_message,
                }

        return {
            "type": "Unknown",
            "description": "未知错误",
            "message": error_message,
        }

    def extract_return_value(self, result: Dict[str, Any]) -> Optional[Any]:
        """提取返回值

        Args:
            result: 执行结果

        Returns:
            返回值
        """
        if result.get("success"):
            return result.get("return_value")
        return None