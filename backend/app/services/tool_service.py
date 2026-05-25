"""工具业务服务

管理 HTTP 工具的创建、更新、执行
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from datetime import datetime

from app.models.tool import Tool, ToolType
from app.tools.http_tool import HttpToolExecutor


class ToolService:
    """工具业务服务"""

    def __init__(self):
        self.http_executor = HttpToolExecutor()

    async def create_http_tool(
        self,
        db: AsyncSession,
        name: str,
        description: str = None,
        config: Dict = None,
        input_schema: Dict = None,
        owner_id: str = None,
        is_public: bool = False,
    ) -> Tool:
        """创建 HTTP 工具"""
        # 验证配置
        if not config:
            config = {}
        if not config.get("url"):
            raise ValueError("URL is required for HTTP tool")

        # 创建工具
        tool = Tool(
            name=name,
            description=description,
            tool_type=ToolType.HTTP,
            config=config,
            input_schema=input_schema,
            owner_id=owner_id,
            is_public=is_public,
            is_enabled=True,
        )

        db.add(tool)
        await db.commit()
        await db.refresh(tool)

        return tool

    async def update_tool(
        self,
        db: AsyncSession,
        tool_id: str,
        name: str = None,
        description: str = None,
        config: Dict = None,
        input_schema: Dict = None,
        is_enabled: bool = None,
        is_public: bool = None,
    ) -> Tool:
        """更新工具"""
        result = await db.execute(select(Tool).where(Tool.id == tool_id))
        tool = result.scalar_one_or_none()

        if not tool:
            raise ValueError(f"Tool '{tool_id}' not found")

        if name:
            tool.name = name
        if description:
            tool.description = description
        if config:
            tool.config = config
        if input_schema:
            tool.input_schema = input_schema
        if is_enabled is not None:
            tool.is_enabled = is_enabled
        if is_public is not None:
            tool.is_public = is_public

        tool.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(tool)

        return tool

    async def delete_tool(
        self,
        db: AsyncSession,
        tool_id: str,
    ):
        """删除工具"""
        result = await db.execute(select(Tool).where(Tool.id == tool_id))
        tool = result.scalar_one_or_none()

        if not tool:
            raise ValueError(f"Tool '{tool_id}' not found")

        await db.delete(tool)
        await db.commit()

    async def get_tool(
        self,
        db: AsyncSession,
        tool_id: str,
    ) -> Optional[Tool]:
        """获取单个工具"""
        result = await db.execute(select(Tool).where(Tool.id == tool_id))
        return result.scalar_one_or_none()

    async def list_tools(
        self,
        db: AsyncSession,
        user_id: str = None,
        tool_type: ToolType = None,
    ) -> List[Tool]:
        """列出工具"""
        query = select(Tool).where(Tool.is_enabled == True)

        if user_id:
            query = query.where(
                or_(Tool.is_public == True, Tool.owner_id == user_id)
            )
        else:
            query = query.where(Tool.is_public == True)

        if tool_type:
            query = query.where(Tool.tool_type == tool_type)

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
                "tool_type": t.tool_type,
                "input_schema": t.input_schema,
            }
            for t in tools
        ]

    async def execute_tool(
        self,
        db: AsyncSession,
        tool_id: str,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行工具"""
        tool = await self.get_tool(db, tool_id)
        if not tool:
            return {"success": False, "error": f"Tool '{tool_id}' not found"}

        if not tool.is_enabled:
            return {"success": False, "error": "Tool is disabled"}

        if tool.tool_type == ToolType.HTTP:
            return await self.http_executor.execute(tool.config, input_data)
        else:
            return {"success": False, "error": f"Unsupported tool type: {tool.tool_type}"}

    async def test_tool(
        self,
        db: AsyncSession,
        tool_id: str,
        input_data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """测试工具执行"""
        return await self.execute_tool(db, tool_id, input_data or {})


# 全局服务实例
tool_service = ToolService()