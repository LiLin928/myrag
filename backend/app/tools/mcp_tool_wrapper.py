"""MCP 工具包装器

封装 MCP SDK 调用，支持：
- SSE/WebSocket 连接
- stdio 进程连接
- 工具列表获取
- 工具调用
"""

from typing import Dict, Any, List
import logging
import httpx

from app.models.mcp_connection import McpConnection, TransportType

logger = logging.getLogger(__name__)


class McpToolWrapper:
    """MCP 工具包装器"""

    async def list_tools(self, connection: McpConnection) -> List[Dict[str, Any]]:
        """获取 MCP Server 的工具列表"""
        if connection.transport_type == TransportType.SSE:
            return await self._list_tools_sse(connection)
        elif connection.transport_type == TransportType.WEBSOCKET:
            return await self._list_tools_ws(connection)
        elif connection.transport_type == TransportType.STDIO:
            return await self._list_tools_stdio(connection)
        else:
            raise ValueError(f"Unsupported transport: {connection.transport_type}")

    async def call_tool(
        self,
        connection: McpConnection,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """调用 MCP 工具"""
        if connection.transport_type == TransportType.SSE:
            return await self._call_tool_sse(connection, tool_name, arguments)
        elif connection.transport_type == TransportType.WEBSOCKET:
            return await self._call_tool_ws(connection, tool_name, arguments)
        elif connection.transport_type == TransportType.STDIO:
            return await self._call_tool_stdio(connection, tool_name, arguments)
        else:
            raise ValueError(f"Unsupported transport: {connection.transport_type}")

    # ==================== SSE 实现 ====================

    async def _list_tools_sse(self, connection: McpConnection) -> List[Dict[str, Any]]:
        """SSE 方式获取工具列表"""
        url = connection.connection_url

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{url}/tools/list",
                    json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                )

                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}")

                data = response.json()
                tools = data.get("result", {}).get("tools", [])

                return [
                    {
                        "name": t.get("name"),
                        "description": t.get("description", ""),
                        "inputSchema": t.get("inputSchema", {}),
                    }
                    for t in tools
                ]

        except Exception as e:
            logger.error(f"SSE list_tools error: {e}")
            raise

    async def _call_tool_sse(
        self,
        connection: McpConnection,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """SSE 方式调用工具"""
        url = connection.connection_url

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{url}/tools/call",
                    json={
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "id": 2,
                        "params": {
                            "name": tool_name,
                            "arguments": arguments,
                        },
                    },
                )

                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                    }

                data = response.json()
                result = data.get("result", {})

                if data.get("error"):
                    return {"success": False, "error": data["error"].get("message")}

                return {
                    "success": True,
                    "output": result.get("content", []),
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== WebSocket 实现 ====================

    async def _list_tools_ws(self, connection: McpConnection) -> List[Dict[str, Any]]:
        """WebSocket 方式获取工具列表"""
        logger.warning("WebSocket transport not fully implemented, using SSE fallback")
        return await self._list_tools_sse(connection)

    async def _call_tool_ws(
        self,
        connection: McpConnection,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """WebSocket 方式调用工具"""
        logger.warning("WebSocket transport not fully implemented, using SSE fallback")
        return await self._call_tool_sse(connection, tool_name, arguments)

    # ==================== stdio 实现 ====================

    async def _list_tools_stdio(self, connection: McpConnection) -> List[Dict[str, Any]]:
        """stdio 方式获取工具列表"""
        logger.warning("stdio transport not fully implemented")
        return []

    async def _call_tool_stdio(
        self,
        connection: McpConnection,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """stdio 方式调用工具"""
        logger.warning("stdio transport not fully implemented")
        return {"success": False, "error": "stdio transport not implemented"}