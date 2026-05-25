"""MCP 连接服务

管理 MCP Server 连接、工具发现、工具同步
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from datetime import datetime
import uuid
import logging

from app.models.mcp_connection import McpConnection, TransportType, SyncStatus
from app.models.tool import Tool, ToolType
from app.tools.mcp_tool_wrapper import McpToolWrapper

logger = logging.getLogger(__name__)


class McpService:
    """MCP 连接服务"""

    def __init__(self):
        self.tool_wrapper = McpToolWrapper()

    async def create_connection(
        self,
        db: AsyncSession,
        name: str,
        description: str = None,
        transport_type: TransportType = TransportType.SSE,
        connection_url: str = None,
        command: str = None,
        args: List[str] = None,
        env_vars: Dict[str, str] = None,
        owner_id: str = None,
        is_public: bool = False,
    ) -> McpConnection:
        """创建 MCP 连接"""
        # 验证配置
        if transport_type in [TransportType.SSE, TransportType.WEBSOCKET]:
            if not connection_url:
                raise ValueError(f"URL is required for {transport_type} transport")
        elif transport_type == TransportType.STDIO:
            if not command:
                raise ValueError("Command is required for stdio transport")

        connection = McpConnection(
            name=name,
            description=description,
            transport_type=transport_type,
            connection_url=connection_url,
            command=command,
            args=args,
            env_vars=env_vars,
            owner_id=uuid.UUID(owner_id) if owner_id else None,
            is_public=is_public,
            is_enabled=True,
            sync_status=SyncStatus.PENDING,
        )

        db.add(connection)
        await db.commit()
        await db.refresh(connection)

        return connection

    async def update_connection(
        self,
        db: AsyncSession,
        connection_id: str,
        **kwargs,
    ) -> McpConnection:
        """更新连接配置"""
        conn_uuid = uuid.UUID(connection_id)
        result = await db.execute(select(McpConnection).where(McpConnection.id == conn_uuid))
        connection = result.scalar_one_or_none()

        if not connection:
            raise ValueError(f"Connection '{connection_id}' not found")

        for key, value in kwargs.items():
            if hasattr(connection, key) and value is not None:
                setattr(connection, key, value)

        connection.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(connection)

        return connection

    async def delete_connection(
        self,
        db: AsyncSession,
        connection_id: str,
    ):
        """删除连接及其关联工具"""
        conn_uuid = uuid.UUID(connection_id)

        # 删除关联的 MCP 工具
        result = await db.execute(
            select(Tool).where(Tool.mcp_connection_id == conn_uuid)
        )
        tools = result.scalars().all()
        for tool in tools:
            await db.delete(tool)

        # 删除连接
        result = await db.execute(select(McpConnection).where(McpConnection.id == conn_uuid))
        connection = result.scalar_one_or_none()
        if connection:
            await db.delete(connection)

        await db.commit()

    async def get_connection(
        self,
        db: AsyncSession,
        connection_id: str,
    ) -> Optional[McpConnection]:
        """获取连接"""
        conn_uuid = uuid.UUID(connection_id)
        result = await db.execute(select(McpConnection).where(McpConnection.id == conn_uuid))
        return result.scalar_one_or_none()

    async def list_connections(
        self,
        db: AsyncSession,
        user_id: str = None,
    ) -> List[McpConnection]:
        """列出用户可见的连接"""
        query = select(McpConnection).where(McpConnection.is_enabled == True)

        if user_id:
            query = query.where(
                or_(McpConnection.is_public == True, McpConnection.owner_id == user_id)
            )
        else:
            query = query.where(McpConnection.is_public == True)

        result = await db.execute(query)
        return result.scalars().all()

    async def list_available_tools(
        self,
        db: AsyncSession,
        user_id: str = None,
    ) -> List[Dict[str, Any]]:
        """获取工作流可用的工具列表"""
        tools = await self.list_tools(db, user_id)
        return [
            {
                "id": str(t.id),
                "name": t.name,
                "description": t.description,
                "tool_type": t.tool_type.value if isinstance(t.tool_type, ToolType) else t.tool_type,
                "input_schema": t.input_schema,
            }
            for t in tools
        ]

    async def list_tools(
        self,
        db: AsyncSession,
        user_id: str = None,
    ) -> List[Tool]:
        """列出用户可见的工具"""
        query = select(Tool).where(Tool.is_enabled == True)

        if user_id:
            query = query.where(
                or_(Tool.is_public == True, Tool.owner_id == user_id)
            )
        else:
            query = query.where(Tool.is_public == True)

        result = await db.execute(query)
        return result.scalars().all()

    async def sync_tools(
        self,
        db: AsyncSession,
        connection_id: str,
    ) -> Dict[str, Any]:
        """同步 MCP Server 的工具列表"""
        connection = await self.get_connection(db, connection_id)
        if not connection:
            return {"success": False, "error": "Connection not found"}

        try:
            # 获取工具列表
            tools = await self.tool_wrapper.list_tools(connection)

            # 删除旧工具
            result = await db.execute(
                select(Tool).where(Tool.mcp_connection_id == uuid.UUID(connection_id))
            )
            old_tools = result.scalars().all()
            for t in old_tools:
                await db.delete(t)

            # 创建新工具
            created_tools = []
            for tool_info in tools:
                tool = Tool(
                    name=f"{connection.name}_{tool_info['name']}",
                    description=tool_info.get("description", ""),
                    tool_type=ToolType.MCP,
                    config={"auto_discovered": True},
                    input_schema=tool_info.get("inputSchema"),
                    mcp_connection_id=uuid.UUID(connection_id),
                    mcp_tool_name=tool_info["name"],
                    is_public=connection.is_public,
                    owner_id=connection.owner_id,
                    is_enabled=True,
                )
                db.add(tool)
                created_tools.append(tool_info["name"])

            # 更新同步状态
            connection.sync_status = SyncStatus.SUCCESS
            connection.last_sync_at = datetime.utcnow()
            connection.sync_error = None

            await db.commit()

            return {
                "success": True,
                "synced_tools": created_tools,
                "count": len(created_tools),
            }

        except Exception as e:
            logger.error(f"MCP sync error: {e}")
            connection.sync_status = SyncStatus.FAILED
            connection.sync_error = str(e)
            await db.commit()

            return {"success": False, "error": str(e)}

    async def get_connection_tools(
        self,
        db: AsyncSession,
        connection_id: str,
    ) -> List[Tool]:
        """获取连接下的工具"""
        conn_uuid = uuid.UUID(connection_id)
        result = await db.execute(
            select(Tool).where(Tool.mcp_connection_id == conn_uuid)
        )
        return result.scalars().all()

    async def test_connection(
        self,
        db: AsyncSession,
        connection_id: str,
    ) -> Dict[str, Any]:
        """测试连接是否可用"""
        connection = await self.get_connection(db, connection_id)
        if not connection:
            return {"success": False, "error": "Connection not found"}

        try:
            tools = await self.tool_wrapper.list_tools(connection)
            return {
                "success": True,
                "available_tools": len(tools),
                "tools": [t["name"] for t in tools],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def execute_mcp_tool(
        self,
        db: AsyncSession,
        tool_id: str,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行 MCP 工具"""
        tool_uuid = uuid.UUID(tool_id)
        result = await db.execute(select(Tool).where(Tool.id == tool_uuid))
        tool = result.scalar_one_or_none()

        if not tool:
            return {"success": False, "error": "Tool not found"}

        if tool.tool_type != ToolType.MCP:
            return {"success": False, "error": "Not an MCP tool"}

        connection = await self.get_connection(db, str(tool.mcp_connection_id))
        if not connection:
            return {"success": False, "error": "MCP connection not found"}

        return await self.tool_wrapper.call_tool(
            connection=connection,
            tool_name=tool.mcp_tool_name,
            arguments=input_data,
        )


# 全局服务实例
mcp_service = McpService()