"""代码执行工具

在 OpenSandbox 安全沙箱中执行 Python 代码
"""

from typing import Dict, Any
from langchain_core.tools import tool

from app.workflow.sandbox.code_executor import get_code_executor


@tool
async def execute_python(
    code: str,
    timeout: int = 30,
) -> Dict[str, Any]:
    """在安全沙箱中执行 Python 代码

    Args:
        code: Python 代码字符串
        timeout: 执行超时时间（秒），默认 30

    Returns:
        执行结果字典，包含：
        - success: 是否成功
        - output: 标准输出
        - error: 错误信息（如有）
        - result: 返回值（如有）

    Note:
        - 限制执行时间（默认30秒）
        - 限制内存使用
        - 禁止危险操作（文件系统、网络）
    """
    code_executor = get_code_executor()

    # 验证代码语法
    validation = await code_executor.validate_code(code)
    if not validation["valid"]:
        return {
            "success": False,
            "output": "",
            "error": validation["error"],
            "result": None,
        }

    # 执行代码
    result = await code_executor.execute(code, timeout=timeout)

    return result


def create_code_execution_tool() -> execute_python:
    """创建代码执行工具实例"""
    return execute_python