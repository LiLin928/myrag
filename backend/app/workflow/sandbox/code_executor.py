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
        import logging
        self.logger = logging.getLogger(__name__)

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
        self.logger.info(f"CodeExecutor: wrapped code length={len(wrapped_code)}")
        self.logger.info(f"CodeExecutor: wrapped code (first 300 chars): {wrapped_code[:300]}")

        # 执行
        raw_result = await self.pool.execute_code(
            code=wrapped_code,
            timeout=timeout,
            packages=packages,
        )

        self.logger.info(f"CodeExecutor: raw_result={raw_result}")

        # 解析结果
        if raw_result.get("success"):
            # 结果可能在 output 或 result 字段中
            output_text = raw_result.get("output", "")
            result_data = raw_result.get("result")

            # 如果 output 为空但 result 有数据，使用 result
            if output_text:
                parsed_result = self.parser.parse(output_text)
            elif result_data:
                parsed_result = {"success": True, "output": result_data, "error": ""}
            else:
                parsed_result = {"success": False, "output": "", "error": "Empty output"}

            self.logger.info(f"CodeExecutor: parsed_result={parsed_result}")
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

        # 使用字符串拼接代替 f-string
        call_code = '''
import json

__FUNCTION_CODE__

result = __FUNCTION_NAME__(*json.loads('__ARGS_JSON__'), **json.loads('__KWARGS_JSON__'))
print(json.dumps({"success": True, "return_value": result}))
'''
        call_code = call_code.replace("__FUNCTION_CODE__", function_code)
        call_code = call_code.replace("__FUNCTION_NAME__", function_name)
        call_code = call_code.replace("__ARGS_JSON__", args_json)
        call_code = call_code.replace("__KWARGS_JSON__", kwargs_json)

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

        # 使用字符串拼接代替 f-string
        context_code = '''
import json

_context = json.loads('__CONTEXT_JSON__')
for key, value in _context.items():
    globals()[key] = value

__USER_CODE__
'''
        context_code = context_code.replace("__CONTEXT_JSON__", context_json)
        context_code = context_code.replace("__USER_CODE__", code)

        return await self.execute(context_code, timeout)

    def _wrap_code(self, code: str) -> str:
        """包装代码，捕获标准输出和执行结果

        Args:
            code: 原始代码

        Returns:
            包装后的代码
        """
        # 清理用户代码的缩进问题
        import textwrap
        cleaned_code = textwrap.dedent(code.strip())

        # 使用 repr() 安全地嵌入代码，避免三引号冲突
        # 或者使用 base64 编码更安全
        import base64
        code_bytes = cleaned_code.encode('utf-8')
        code_b64 = base64.b64encode(code_bytes).decode('utf-8')

        # 包装器：解码并执行用户代码
        wrapper = '''
import sys
import io
import json
import base64

# 保存原始 stdout
_original_stdout = sys.stdout

# 捕获标准输出（用于捕获用户代码的 print 输出）
_stdout_capture = io.StringIO()
sys.stdout = _stdout_capture

# 解码并执行用户代码
_user_code = base64.b64decode("__CODE_B64__").decode('utf-8')
try:
    exec(_user_code, globals())
    exec_error = None
except Exception as e:
    exec_error = str(e)

# 恢复 stdout（必须在 print 结果之前恢复）
sys.stdout = _original_stdout

# 获取用户代码的输出
_output = _stdout_capture.getvalue()

# 尝试从 globals 获取 result（用户代码定义的）
_result = globals().get('result', None)

# 输出结果到原始 stdout
print(json.dumps({
    "success": exec_error is None,
    "output": _output,
    "result": _result,
    "error": exec_error
}))
'''
        return wrapper.replace('__CODE_B64__', code_b64)

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