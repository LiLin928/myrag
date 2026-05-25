"""Agent 会话管理 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional
import uuid
import datetime as dt

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.db import get_db
from app.models.agent import Agent
from app.models.agent_session import AgentSession
from app.schemas.agent_chat import SessionResponse, SessionMessage

router = APIRouter(prefix="/agent-sessions", tags=["agent-sessions"])


@router.get("/history", response_model=List[SessionResponse])
async def list_all_sessions(
    agent_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有会话历史（跨 Agent）"""
    # 构建查询条件
    conditions = [AgentSession.user_id == current_user.id]

    if agent_id:
        try:
            aid = uuid.UUID(agent_id)
            conditions.append(AgentSession.agent_id == aid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid agent_id format")

    if start_date:
        try:
            start_dt = dt.datetime.fromisoformat(start_date)
            conditions.append(AgentSession.updated_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format, use ISO format")

    if end_date:
        try:
            end_dt = dt.datetime.fromisoformat(end_date)
            conditions.append(AgentSession.updated_at <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format, use ISO format")

    # 分页查询
    offset = (page - 1) * page_size
    result = await db.execute(
        select(AgentSession, Agent.name)
        .join(Agent, AgentSession.agent_id == Agent.id)
        .where(and_(*conditions))
        .order_by(AgentSession.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = result.all()

    return [
        SessionResponse(
            id=str(session.id),
            agent_id=str(session.agent_id),
            thread_id=session.thread_id,
            title=session.title or f"会话 ({session.created_at.strftime('%Y-%m-%d')})",
            message_count=session.message_count,
            messages=[],
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
        for session, agent_name in rows
    ]


@router.get("/history/{session_id}", response_model=SessionResponse)
async def get_session_detail(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取会话详情"""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id format")

    result = await db.execute(
        select(AgentSession)
        .where(and_(AgentSession.id == sid, AgentSession.user_id == current_user.id))
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = [
        SessionMessage(
            role=m["role"],
            content=m["content"],
            sources=m.get("sources", []),
            tool_calls=m.get("tool_calls", []),
            created_at=session.created_at,
        )
        for m in (session.messages or [])
    ]

    return SessionResponse(
        id=str(session.id),
        agent_id=str(session.agent_id),
        thread_id=session.thread_id,
        title=session.title,
        message_count=session.message_count,
        messages=messages,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.delete("/history/{session_id}")
async def delete_session_by_id(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除会话"""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id format")

    result = await db.execute(
        select(AgentSession)
        .where(and_(AgentSession.id == sid, AgentSession.user_id == current_user.id))
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.delete(session)
    await db.commit()

    return {"message": "Session deleted"}