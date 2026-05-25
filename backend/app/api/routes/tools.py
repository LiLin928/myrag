"""工具管理 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.tool import Tool, ToolType
from app.services.tool_service import tool_service
from app.db import get_db

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/")
async def list_tools(
    tool_type: Optional[ToolType] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取工具列表"""
    tools = await tool_service.list_tools(
        db=db,
        user_id=str(current_user.id),
        tool_type=tool_type,
    )

    return [
        {
            "id": str(t.id),
            "name": t.name,
            "description": t.description,
            "tool_type": t.tool_type,
            "config": t.config,
            "input_schema": t.input_schema,
            "is_public": t.is_public,
            "is_enabled": t.is_enabled,
            "owner_id": str(t.owner_id) if t.owner_id else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tools
    ]


@router.get("/available")
async def list_available_tools(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取工作流可用的工具列表"""
    tools = await tool_service.list_available_tools(
        db=db,
        user_id=str(current_user.id),
    )
    return tools


@router.get("/{tool_id}")
async def get_tool(
    tool_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取工具详情"""
    tool = await tool_service.get_tool(db, tool_id)

    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    if not tool.is_public and tool.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": str(tool.id),
        "name": tool.name,
        "description": tool.description,
        "tool_type": tool.tool_type,
        "config": tool.config,
        "input_schema": tool.input_schema,
        "output_schema": tool.output_schema,
        "is_public": tool.is_public,
        "is_enabled": tool.is_enabled,
        "owner_id": str(tool.owner_id) if tool.owner_id else None,
        "created_at": tool.created_at.isoformat() if tool.created_at else None,
        "updated_at": tool.updated_at.isoformat() if tool.updated_at else None,
    }


@router.post("/")
async def create_tool(
    name: str = Body(...),
    description: str = Body(None),
    config: Dict[str, Any] = Body(...),
    input_schema: Dict[str, Any] = Body(None),
    is_public: bool = Body(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建 HTTP 工具"""
    try:
        tool = await tool_service.create_http_tool(
            db=db,
            name=name,
            description=description,
            config=config,
            input_schema=input_schema,
            owner_id=str(current_user.id),
            is_public=is_public,
        )

        return {
            "id": str(tool.id),
            "name": tool.name,
            "description": tool.description,
            "tool_type": tool.tool_type,
            "is_public": tool.is_public,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{tool_id}")
async def update_tool(
    tool_id: str,
    name: str = Body(None),
    description: str = Body(None),
    config: Dict[str, Any] = Body(None),
    input_schema: Dict[str, Any] = Body(None),
    is_enabled: bool = Body(None),
    is_public: bool = Body(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新工具"""
    tool = await tool_service.get_tool(db, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    if tool.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can update")

    try:
        updated_tool = await tool_service.update_tool(
            db=db,
            tool_id=tool_id,
            name=name,
            description=description,
            config=config,
            input_schema=input_schema,
            is_enabled=is_enabled,
            is_public=is_public,
        )

        return {
            "id": str(updated_tool.id),
            "name": updated_tool.name,
            "description": updated_tool.description,
            "is_enabled": updated_tool.is_enabled,
            "is_public": updated_tool.is_public,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{tool_id}")
async def delete_tool(
    tool_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除工具"""
    tool = await tool_service.get_tool(db, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    if tool.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can delete")

    await tool_service.delete_tool(db, tool_id)
    return {"deleted": tool_id}


@router.patch("/{tool_id}/enable")
async def toggle_enable(
    tool_id: str,
    is_enabled: bool = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """启用/禁用工具"""
    tool = await tool_service.get_tool(db, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    if tool.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can toggle")

    updated_tool = await tool_service.update_tool(
        db=db,
        tool_id=tool_id,
        is_enabled=is_enabled,
    )

    return {
        "id": str(updated_tool.id),
        "is_enabled": updated_tool.is_enabled,
    }


@router.post("/{tool_id}/test")
async def test_tool(
    tool_id: str,
    input_data: Dict[str, Any] = Body(default={}),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """测试工具执行"""
    tool = await tool_service.get_tool(db, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    if not tool.is_public and tool.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await tool_service.test_tool(
        db=db,
        tool_id=tool_id,
        input_data=input_data,
    )

    return result