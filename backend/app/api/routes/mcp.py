"""MCP Connection 管理 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.mcp_connection import McpConnection, TransportType, SyncStatus
from app.services.mcp_service import mcp_service
from app.dependencies import get_db

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/connections")
async def list_connections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户可见的 MCP 连接列表"""
    connections = await mcp_service.list_connections(
        db=db,
        user_id=str(current_user.id),
    )

    return [
        {
            "id": str(c.id),
            "name": c.name,
            "description": c.description,
            "transport_type": c.transport_type.value if c.transport_type else None,
            "is_enabled": c.is_enabled,
            "is_public": c.is_public,
            "sync_status": c.sync_status.value if c.sync_status else None,
            "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
        }
        for c in connections
    ]


@router.get("/connections/{connection_id}")
async def get_connection(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个 MCP 连接详情"""
    connection = await mcp_service.get_connection(db, connection_id)

    if not connection:
        raise HTTPException(status_code=404, detail="MCP connection not found")

    # 检查访问权限
    if not connection.is_public and connection.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": str(connection.id),
        "name": connection.name,
        "description": connection.description,
        "transport_type": connection.transport_type.value if connection.transport_type else None,
        "connection_url": connection.connection_url,
        "command": connection.command,
        "args": connection.args,
        "env_vars": connection.env_vars,
        "is_enabled": connection.is_enabled,
        "is_public": connection.is_public,
        "owner_id": str(connection.owner_id) if connection.owner_id else None,
        "sync_status": connection.sync_status.value if connection.sync_status else None,
        "sync_error": connection.sync_error,
        "last_sync_at": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
        "created_at": connection.created_at.isoformat() if connection.created_at else None,
        "updated_at": connection.updated_at.isoformat() if connection.updated_at else None,
    }


@router.post("/connections")
async def create_connection(
    name: str = Body(...),
    description: str = Body(None),
    transport_type: TransportType = Body(TransportType.SSE),
    connection_url: str = Body(None),
    command: str = Body(None),
    args: List[str] = Body(None),
    env_vars: Dict[str, str] = Body(None),
    is_public: bool = Body(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建新的 MCP 连接"""
    try:
        connection = await mcp_service.create_connection(
            db=db,
            name=name,
            description=description,
            transport_type=transport_type,
            connection_url=connection_url,
            command=command,
            args=args,
            env_vars=env_vars,
            owner_id=str(current_user.id),
            is_public=is_public,
        )

        return {
            "id": str(connection.id),
            "name": connection.name,
            "description": connection.description,
            "transport_type": connection.transport_type.value if connection.transport_type else None,
            "is_enabled": connection.is_enabled,
            "is_public": connection.is_public,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/connections/{connection_id}")
async def update_connection(
    connection_id: str,
    name: str = Body(None),
    description: str = Body(None),
    transport_type: TransportType = Body(None),
    connection_url: str = Body(None),
    command: str = Body(None),
    args: List[str] = Body(None),
    env_vars: Dict[str, str] = Body(None),
    is_enabled: bool = Body(None),
    is_public: bool = Body(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新 MCP 连接配置（仅限所有者）"""
    connection = await mcp_service.get_connection(db, connection_id)

    if not connection:
        raise HTTPException(status_code=404, detail="MCP connection not found")

    if connection.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can update")

    try:
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if transport_type is not None:
            update_data["transport_type"] = transport_type
        if connection_url is not None:
            update_data["connection_url"] = connection_url
        if command is not None:
            update_data["command"] = command
        if args is not None:
            update_data["args"] = args
        if env_vars is not None:
            update_data["env_vars"] = env_vars
        if is_enabled is not None:
            update_data["is_enabled"] = is_enabled
        if is_public is not None:
            update_data["is_public"] = is_public

        updated_connection = await mcp_service.update_connection(
            db=db,
            connection_id=connection_id,
            **update_data,
        )

        return {
            "id": str(updated_connection.id),
            "name": updated_connection.name,
            "description": updated_connection.description,
            "transport_type": updated_connection.transport_type.value if updated_connection.transport_type else None,
            "is_enabled": updated_connection.is_enabled,
            "is_public": updated_connection.is_public,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/connections/{connection_id}")
async def delete_connection(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除 MCP 连接（仅限所有者）"""
    connection = await mcp_service.get_connection(db, connection_id)

    if not connection:
        raise HTTPException(status_code=404, detail="MCP connection not found")

    if connection.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can delete")

    await mcp_service.delete_connection(db, connection_id)
    return {"deleted": connection_id}


@router.post("/connections/{connection_id}/sync")
async def sync_tools(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """同步 MCP Server 的工具列表"""
    connection = await mcp_service.get_connection(db, connection_id)

    if not connection:
        raise HTTPException(status_code=404, detail="MCP connection not found")

    # 检查访问权限
    if not connection.is_public and connection.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await mcp_service.sync_tools(db, connection_id)
    return result


@router.get("/connections/{connection_id}/tools")
async def get_connection_tools(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取 MCP 连接下的工具列表"""
    connection = await mcp_service.get_connection(db, connection_id)

    if not connection:
        raise HTTPException(status_code=404, detail="MCP connection not found")

    # 检查访问权限
    if not connection.is_public and connection.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    tools = await mcp_service.get_connection_tools(db, connection_id)

    return [
        {
            "id": str(t.id),
            "name": t.name,
            "description": t.description,
            "mcp_tool_name": t.mcp_tool_name,
            "input_schema": t.input_schema,
            "is_enabled": t.is_enabled,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tools
    ]


@router.post("/connections/{connection_id}/test")
async def test_connection(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """测试 MCP 连接是否可用"""
    connection = await mcp_service.get_connection(db, connection_id)

    if not connection:
        raise HTTPException(status_code=404, detail="MCP connection not found")

    # 检查访问权限
    if not connection.is_public and connection.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await mcp_service.test_connection(db, connection_id)
    return result