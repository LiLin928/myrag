# backend/tests/graphs/test_tool_registry.py

import pytest
from app.tools.tool_registry import ToolRegistry


def test_tool_registry_init():
    """测试工具注册表初始化"""
    registry = ToolRegistry()
    assert registry is not None


def test_default_tools_registered():
    """测试默认工具已注册"""
    registry = ToolRegistry()
    tools = registry.get_tools()

    # 验证三个基础工具
    assert len(tools) >= 3

    tool_names = registry.get_tool_names()
    assert "knowledge_search" in tool_names
    assert "execute_python" in tool_names
    assert "http_request" in tool_names


def test_get_tool_by_name():
    """测试按名称获取工具"""
    registry = ToolRegistry()

    tool = registry.get_tool_by_name("knowledge_search")
    assert tool is not None

    # 验证工具是 LangChain Tool
    from langchain_core.tools import BaseTool
    assert isinstance(tool, BaseTool)


def test_register_custom_tool():
    """测试注册自定义工具"""
    registry = ToolRegistry()

    from langchain_core.tools import tool

    @tool
    def custom_tool(x: int) -> int:
        """自定义测试工具"""
        return x * 2

    registry.register_tool("custom", custom_tool)

    assert registry.get_tool_by_name("custom") is not None


def test_unregister_tool():
    """测试注销工具"""
    registry = ToolRegistry()

    from langchain_core.tools import tool

    @tool
    def temp_tool(x: int) -> int:
        """临时测试工具"""
        return x

    registry.register_tool("temp", temp_tool)
    assert registry.get_tool_by_name("temp") is not None

    registry.unregister_tool("temp")
    assert registry.get_tool_by_name("temp") is None


def test_has_tool():
    """测试检查工具是否存在"""
    registry = ToolRegistry()

    assert registry.has_tool("knowledge_search") is True
    assert registry.has_tool("nonexistent") is False