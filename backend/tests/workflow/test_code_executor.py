# backend/tests/workflow/test_code_executor.py

import pytest
from app.workflow.sandbox.code_executor import CodeExecutor, get_code_executor
from app.workflow.sandbox.result_parser import ResultParser


def test_result_parser_parse_json():
    """测试解析 JSON 输出"""
    parser = ResultParser()

    output = '{"success": true, "output": "hello"}'
    result = parser.parse(output)

    assert result["success"] is True
    assert result["output"] == "hello"


def test_result_parser_parse_text():
    """测试解析纯文本"""
    parser = ResultParser()

    output = "plain text output"
    result = parser.parse(output)

    assert result["success"] is True
    assert result["output"] == "plain text output"


def test_result_parser_parse_empty():
    """测试解析空输出"""
    parser = ResultParser()

    result = parser.parse("")
    assert result["success"] is False
    assert result["error"] == "Empty output"


def test_result_parser_parse_error():
    """测试解析错误"""
    parser = ResultParser()

    error_msg = "SyntaxError: invalid syntax"
    result = parser.parse_error(error_msg)

    assert result["type"] == "SyntaxError"
    assert result["description"] == "语法错误"


def test_code_executor_init():
    """测试代码执行器初始化"""
    executor = CodeExecutor()
    assert executor is not None
    assert executor.parser is not None


def test_code_executor_methods():
    """测试方法存在"""
    executor = CodeExecutor()
    assert hasattr(executor, 'execute')
    assert hasattr(executor, 'execute_function')
    assert hasattr(executor, 'execute_with_context')
    assert hasattr(executor, 'validate_code')


@pytest.mark.asyncio
async def test_code_executor_validate():
    """测试代码验证"""
    executor = CodeExecutor()

    # 有效代码
    result = await executor.validate_code("print('hello')")
    assert result["valid"] is True

    # 无效代码
    result = await executor.validate_code("print(")
    assert result["valid"] is False
    assert result["error"] is not None


def test_get_code_executor():
    """测试获取代码执行器实例"""
    executor = get_code_executor()
    assert executor is not None
    assert isinstance(executor, CodeExecutor)