"""Agent 工具注册表

管理 Agent 可用的工具集，支持：
- 默认工具注册
- 自定义工具注册
- 工具查找和列表
"""

from typing import Dict, List, Optional
from langchain_core.tools import BaseTool

from app.tools.knowledge_search import create_knowledge_search_tools
from app.tools.http_request import create_http_request_tool
from app.tools.code_execution import create_code_execution_tool


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """注册默认工具集

        基础工具包括：
        - knowledge_search: 知识检索
        - search_by_supplier: 按供应商检索
        - search_by_clause_type: 按条款类型检索
        - search_all_projects: 跨项目检索
        - execute_python: 代码执行（沙箱）
        - http_request: HTTP 请求
        """
        # 注册知识检索工具
        knowledge_tools = create_knowledge_search_tools()
        for tool_func in knowledge_tools:
            self.register_tool(tool_func.name, tool_func)

        # 注册代码执行工具
        self.register_tool("execute_python", create_code_execution_tool())

        # 注册 HTTP 请求工具
        self.register_tool("http_request", create_http_request_tool())

    def register_tool(self, name: str, tool: BaseTool):
        """注册工具

        Args:
            name: 工具名称
            tool: LangChain BaseTool 实例
        """
        self._tools[name] = tool

    def unregister_tool(self, name: str):
        """注销工具

        Args:
            name: 工具名称
        """
        if name in self._tools:
            del self._tools[name]

    def get_tools(self) -> List[BaseTool]:
        """获取所有工具列表

        Returns:
            工具列表
        """
        return list(self._tools.values())

    def get_tool_names(self) -> List[str]:
        """获取所有工具名称列表

        Returns:
            工具名称列表
        """
        return list(self._tools.keys())

    def get_tool_by_name(self, name: str) -> Optional[BaseTool]:
        """按名称获取工具

        Args:
            name: 工具名称

        Returns:
            工具实例，不存在则返回 None
        """
        return self._tools.get(name)

    def has_tool(self, name: str) -> bool:
        """检查工具是否存在

        Args:
            name: 工具名称

        Returns:
            是否存在
        """
        return name in self._tools


# 全局工具注册表实例
tool_registry = ToolRegistry()


def get_all_tools() -> List[BaseTool]:
    """获取所有已注册的工具列表

    这是工具注册表的快捷访问函数。

    Returns:
        工具列表
    """
    return tool_registry.get_tools()