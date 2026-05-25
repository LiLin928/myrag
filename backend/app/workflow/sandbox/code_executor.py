"""代码执行器

封装 SandboxPool，提供更高级的代码执行接口
"""

from typing import Dict, Any, List, Optional
import json
import ast

from app.workflow.sandbox.sandbox_pool import get_sandbox_pool
from app.workflow.sandbox.result_parser import ResultParser


class CodeExecutor:
    """代码执行器"""

    def __init__(self):
        self.parser = ResultParser()
        self.pool = get_sandbox_pool()

    async def execute(
        self,
        code: str,
        timeout: int = 30,
        packages: List[str] = None,
    ) -> Dict[str, Any]:
        """执行 Python 代码

        Args:
            code: Python 代码字符串
            timeout: 执行超时（秒）
            packages: 预安装包列表

        Returns:
            执行结果：{"success": bool, "output": str, "error": str}
        """
        # 包装代码，捕获输出
        wrapped_code = self._wrap_code(code)

        # 执行
        raw_result = await self.pool.execute_code(
            code=wrapped_code,
            timeout=timeout,
            packages=packages,
        )

        # 解析结果
        if raw_result.get("success"):
            parsed_result = self.parser.parse(raw_result.get("output", ""))
            return parsed_result
        else:
            return raw_result

    async def execute_function(
        self,
        function_code: str,
        function_name: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """执行函数

        Args:
            function_code: 函数定义代码
            function_name: 函数名称
            args: 函数参数（列表）
            kwargs: 函数参数（字典）
            timeout: 执行超时

        Returns:
            执行结果
        """
        args_json = json.dumps(args or [])
        kwargs_json = json.dumps(kwargs or {})

        call_code = f'''
import json

{function_code}

result = {function_name}(*json.loads('{args_json}'), **json.loads('{kwargs_json}'))
print(json.dumps({"success": True, "return_value": result}))
'''

        return await self.execute(call_code, timeout)

    async def execute_with_context(
        self,
        code: str,
        context: Dict[str, Any],
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """带上下文执行

        Args:
            code: Python 代码
            context: 上下文变量
            timeout: 执行超时

        Returns:
            执行结果
        """
        context_json = json.dumps(context)

        context_code = f'''
import json

_context = json.loads('{context_json}')
for key, value in _context.items():
    globals()[key] = value

{code}
'''

        return await self.execute(context_code, timeout)

    def _wrap_code(self, code: str) -> str:
        """包装代码，捕获标准输出

        Args:
            code: 原始代码

        Returns:
            包装后的代码
        """
        return f'''
import sys
import io
import json

# 捕获标准输出
_stdout_capture = io.StringIO()
sys.stdout = _stdout_capture

try:
    {code}

    output = _stdout_capture.getvalue()
    print(json.dumps({
        "success": True,
        "output": output,
        "error": None
    }))

except Exception as e:
    print(json.dumps({
        "success": False,
        "output": "",
        "error": str(e)
    }))
'''

    async def validate_code(self, code: str) -> Dict[str, Any]:
        """验证代码语法

        Args:
            code: Python 代码

        Returns:
            验证结果
        """
        try:
            ast.parse(code)
            return {
                "valid": True,
                "error": None,
            }
        except SyntaxError as e:
            return {
                "valid": False,
                "error": str(e),
                "line": e.lineno,
            }


# 全局执行器实例（延迟初始化）
_code_executor: Optional[CodeExecutor] = None


def get_code_executor() -> CodeExecutor:
    """获取代码执行器实例（延迟初始化）"""
    global _code_executor
    if _code_executor is None:
        _code_executor = CodeExecutor()
    return _code_executor