"""Agent 发布管理 API 路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List
import uuid
import secrets
import json

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.db import get_db
from app.models.agent import Agent
from app.models.agent_publish import AgentPublish
from app.schemas.agent_publish import PublishRequest, PublishResponse, PublishListResponse

router = APIRouter(prefix="/agent-publish", tags=["agent-publish"])


@router.post("/{agent_id}", response_model=PublishResponse)
async def publish_agent(
    agent_id: str,
    data: PublishRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发布智能体"""
    try:
        aid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent_id format")

    # 验证 Agent
    result = await db.execute(
        select(Agent).where(and_(Agent.id == aid, Agent.user_id == current_user.id))
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 生成发布内容
    publish_id = str(uuid.uuid4())
    embed_code = None
    link_url = None
    api_key = None

    if data.publish_type == "embed":
        config = data.config or {}
        theme = config.get("theme_color", "#1890ff")
        title = config.get("window_title", agent.name)
        position = config.get("position", "bottom-right")

        embed_code = f'''<script>
(function(d,s,id){{var js,fjs=d.getElementsByTagName(s)[0];js=d.createElement(s);js.id=id;js.src='https://your-host/public/sdk/{publish_id}.js';fjs.parentNode.insertBefore(js,fjs);}})(document,'script','myrag-agent-sdk');window.MyRAGAgent.init({{theme:'{theme}',title:'{title}',position:'{position}'}});</script>'''

    elif data.publish_type == "link":
        link_url = f"https://your-host/public/chat/{publish_id}"

    elif data.publish_type == "api":
        api_key = secrets.token_urlsafe(32)

    # 创建发布记录
    publish = AgentPublish(
        id=publish_id,
        agent_id=agent.id,
        publish_type=data.publish_type,
        embed_code=embed_code,
        link_url=link_url,
        api_key=api_key,
        config=json.dumps(data.config) if data.config else None,
        status="active",
    )
    db.add(publish)
    await db.commit()
    await db.refresh(publish)

    return PublishResponse(
        id=str(publish.id),
        agent_id=str(publish.agent_id),
        publish_type=publish.publish_type,
        embed_code=publish.embed_code,
        link_url=publish.link_url,
        api_key=publish.api_key,
        status=publish.status,
        access_count=publish.access_count,
        created_at=publish.created_at,
    )


@router.get("/", response_model=List[PublishListResponse])
async def list_publishes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取发布列表"""
    result = await db.execute(
        select(AgentPublish, Agent.name)
        .join(Agent, AgentPublish.agent_id == Agent.id)
        .where(Agent.user_id == current_user.id)
        .order_by(AgentPublish.created_at.desc())
    )
    rows = result.all()

    return [
        PublishListResponse(
            id=str(publish.id),
            agent_name=agent_name,
            publish_type=publish.publish_type,
            status=publish.status,
            access_count=publish.access_count,
            created_at=publish.created_at,
        )
        for publish, agent_name in rows
    ]


@router.put("/{publish_id}")
async def update_publish_status(
    publish_id: str,
    status: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新发布状态"""
    try:
        pid = uuid.UUID(publish_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid publish_id format")

    if status not in ["active", "disabled"]:
        raise HTTPException(status_code=400, detail="Invalid status, must be 'active' or 'disabled'")

    result = await db.execute(
        select(AgentPublish)
        .join(Agent, AgentPublish.agent_id == Agent.id)
        .where(and_(AgentPublish.id == pid, Agent.user_id == current_user.id))
    )
    publish = result.scalar_one_or_none()

    if not publish:
        raise HTTPException(status_code=404, detail="Publish not found")

    publish.status = status
    await db.commit()

    return {"id": str(publish.id), "status": status}


@router.delete("/{publish_id}")
async def delete_publish(
    publish_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除发布"""
    try:
        pid = uuid.UUID(publish_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid publish_id format")

    result = await db.execute(
        select(AgentPublish)
        .join(Agent, AgentPublish.agent_id == Agent.id)
        .where(and_(AgentPublish.id == pid, Agent.user_id == current_user.id))
    )
    publish = result.scalar_one_or_none()

    if not publish:
        raise HTTPException(status_code=404, detail="Publish not found")

    await db.delete(publish)
    await db.commit()

    return {"message": "Publish deleted"}