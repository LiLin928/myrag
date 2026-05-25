"""Agent API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid
import datetime as dt

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.db import get_db
from app.models.agent import Agent
from app.models.agent_binding import AgentKnowledgeBinding, AgentToolBinding, AgentSkillBinding
from app.models.agent_session import AgentSession
from app.models.model_config import ModelConfig
from app.models.knowledge_base import KnowledgeBase
from app.models.skill import Skill
from app.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentListResponse,
    KnowledgeBindingResponse,
)
from app.schemas.agent_chat import (
    ChatRequest,
    ChatResponse,
    SessionResponse,
    SessionMessage,
    SourceReference,
    ToolCall,
)
from app.services.agent_service import agent_service
from app.services.agent_engine import AgentEngine

router = APIRouter(prefix="/agents", tags=["agents"])


# ============= CRUD API =============

@router.get("/", response_model=List[AgentListResponse])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取智能体列表"""
    result = await db.execute(
        select(Agent, ModelConfig.name)
        .join(ModelConfig, Agent.model_id == ModelConfig.id)
        .where(Agent.user_id == current_user.id)
        .order_by(Agent.updated_at.desc())
    )
    rows = result.all()

    return [
        AgentListResponse(
            id=str(agent.id),
            name=agent.name,
            description=agent.description,
            model_name=model_name,
            use_knowledge=agent.use_knowledge,
            use_tools=agent.use_tools,
            use_skills=agent.use_skills,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )
        for agent, model_name in rows
    ]


@router.post("/", response_model=AgentResponse)
async def create_agent(
    data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建智能体"""
    # 验证模型是否存在
    try:
        model_uuid = uuid.UUID(data.model_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid model_id format")

    model_result = await db.execute(
        select(ModelConfig).where(ModelConfig.id == model_uuid)
    )
    model = model_result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # 创建 Agent
    agent = Agent(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        model_id=str(model_uuid),
        system_prompt=data.system_prompt,
        use_knowledge=data.use_knowledge,
        use_tools=data.use_tools,
        use_skills=data.use_skills,
    )
    db.add(agent)
    await db.flush()

    # 添加知识库绑定
    for kb_data in data.knowledge_bindings:
        try:
            kb_uuid = uuid.UUID(kb_data.knowledge_base_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid knowledge_base_id: {kb_data.knowledge_base_id}")

        kb_result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_uuid)
        )
        kb = kb_result.scalar_one_or_none()
        if not kb:
            raise HTTPException(status_code=404, detail=f"Knowledge base not found: {kb_data.knowledge_base_id}")

        binding = AgentKnowledgeBinding(
            agent_id=agent.id,
            knowledge_base_id=str(kb_uuid),
            search_type=kb_data.search_type,
            top_k=kb_data.top_k,
            score_threshold=kb_data.score_threshold,
            priority=kb_data.priority,
        )
        db.add(binding)

    # 添加工具绑定
    for tool_name in data.tool_bindings:
        binding = AgentToolBinding(
            agent_id=agent.id,
            tool_name=tool_name,
        )
        db.add(binding)

    # 添加 Skills 绑定
    for skill_id in data.skill_bindings:
        try:
            skill_uuid = uuid.UUID(skill_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid skill_id: {skill_id}")

        binding = AgentSkillBinding(
            agent_id=agent.id,
            skill_id=str(skill_uuid),
        )
        db.add(binding)

    await db.commit()
    await db.refresh(agent)

    return await _build_agent_response(agent, db)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取智能体详情"""
    try:
        aid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent_id format")

    result = await db.execute(
        select(Agent)
        .where(and_(Agent.id == aid, Agent.user_id == current_user.id))
        .options(
            selectinload(Agent.knowledge_bindings),
            selectinload(Agent.tool_bindings),
            selectinload(Agent.skill_bindings),
        )
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return await _build_agent_response(agent, db)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新智能体"""
    try:
        aid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent_id format")

    result = await db.execute(
        select(Agent)
        .where(and_(Agent.id == aid, Agent.user_id == current_user.id))
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 更新基础字段
    if data.name is not None:
        agent.name = data.name
    if data.description is not None:
        agent.description = data.description
    if data.model_id is not None:
        try:
            model_uuid = uuid.UUID(data.model_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid model_id format")
        agent.model_id = str(model_uuid)
    if data.system_prompt is not None:
        agent.system_prompt = data.system_prompt
    if data.use_knowledge is not None:
        agent.use_knowledge = data.use_knowledge
    if data.use_tools is not None:
        agent.use_tools = data.use_tools
    if data.use_skills is not None:
        agent.use_skills = data.use_skills
    if data.search_type is not None:
        agent.search_type = data.search_type
    if data.top_k is not None:
        agent.top_k = data.top_k
    if data.score_threshold is not None:
        agent.score_threshold = data.score_threshold

    # 更新知识库绑定（先删后增）
    if data.knowledge_bindings is not None:
        await db.execute(
            select(AgentKnowledgeBinding).where(AgentKnowledgeBinding.agent_id == aid)
        )
        # 删除旧绑定
        old_kb_result = await db.execute(
            select(AgentKnowledgeBinding).where(AgentKnowledgeBinding.agent_id == aid)
        )
        for old_kb in old_kb_result.scalars().all():
            await db.delete(old_kb)

        # 添加新绑定
        for kb_data in data.knowledge_bindings:
            try:
                kb_uuid = uuid.UUID(kb_data.knowledge_base_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid knowledge_base_id")

            binding = AgentKnowledgeBinding(
                agent_id=agent.id,
                knowledge_base_id=str(kb_uuid),
                search_type=kb_data.search_type,
                top_k=kb_data.top_k,
                score_threshold=kb_data.score_threshold,
                priority=kb_data.priority,
            )
            db.add(binding)

    # 更新工具绑定
    if data.tool_bindings is not None:
        old_tool_result = await db.execute(
            select(AgentToolBinding).where(AgentToolBinding.agent_id == aid)
        )
        for old_tool in old_tool_result.scalars().all():
            await db.delete(old_tool)

        for tool_name in data.tool_bindings:
            binding = AgentToolBinding(agent_id=agent.id, tool_name=tool_name)
            db.add(binding)

    # 更新 Skills 绑定
    if data.skill_bindings is not None:
        old_skill_result = await db.execute(
            select(AgentSkillBinding).where(AgentSkillBinding.agent_id == aid)
        )
        for old_skill in old_skill_result.scalars().all():
            await db.delete(old_skill)

        for skill_id in data.skill_bindings:
            try:
                skill_uuid = uuid.UUID(skill_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid skill_id")

            binding = AgentSkillBinding(agent_id=agent.id, skill_id=str(skill_uuid))
            db.add(binding)

    await db.commit()
    await db.refresh(agent)

    return await _build_agent_response(agent, db)


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除智能体"""
    try:
        aid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent_id format")

    result = await db.execute(
        select(Agent).where(and_(Agent.id == aid, Agent.user_id == current_user.id))
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    await db.delete(agent)
    await db.commit()

    return {"message": "Agent deleted"}


async def _build_agent_response(agent: Agent, db: AsyncSession) -> AgentResponse:
    """构建 Agent 响应"""
    # 获取模型名称
    model_result = await db.execute(
        select(ModelConfig.name).where(ModelConfig.id == agent.model_id)
    )
    model_name = model_result.scalar()

    # 获取知识库绑定
    kb_bindings_result = await db.execute(
        select(AgentKnowledgeBinding, KnowledgeBase.name)
        .join(KnowledgeBase, AgentKnowledgeBinding.knowledge_base_id == KnowledgeBase.id)
        .where(AgentKnowledgeBinding.agent_id == agent.id)
    )
    kb_bindings = kb_bindings_result.all()

    knowledge_binding_responses = [
        KnowledgeBindingResponse(
            id=str(binding.id),
            agent_id=str(binding.agent_id),
            knowledge_base_id=str(binding.knowledge_base_id),
            knowledge_base_name=kb_name,
            search_type=binding.search_type,
            top_k=binding.top_k,
            score_threshold=binding.score_threshold,
            priority=binding.priority,
            created_at=binding.created_at,
        )
        for binding, kb_name in kb_bindings
    ]

    # 获取工具绑定
    tool_bindings_result = await db.execute(
        select(AgentToolBinding.tool_name).where(AgentToolBinding.agent_id == agent.id)
    )
    tool_bindings = [row[0] for row in tool_bindings_result.all()]

    # 获取 Skills 绑定（返回 skill_id）
    skill_bindings_result = await db.execute(
        select(AgentSkillBinding.skill_id).where(AgentSkillBinding.agent_id == agent.id)
    )
    skill_bindings = [str(row[0]) for row in skill_bindings_result.all()]

    return AgentResponse(
        id=str(agent.id),
        user_id=str(agent.user_id),
        name=agent.name,
        description=agent.description,
        model_id=str(agent.model_id),
        model_name=model_name,
        system_prompt=agent.system_prompt,
        use_knowledge=agent.use_knowledge,
        use_tools=agent.use_tools,
        use_skills=agent.use_skills,
        search_type=agent.search_type,
        top_k=agent.top_k,
        score_threshold=agent.score_threshold,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        knowledge_bindings=knowledge_binding_responses,
        tool_bindings=tool_bindings,
        skill_bindings=skill_bindings,
    )


# ============= Agent-specific Chat API (using AgentEngine) =============

@router.post("/{agent_id}/chat", response_model=ChatResponse)
async def chat_with_agent(
    agent_id: str,
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发起对话（创建新会话）"""
    try:
        aid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent_id format")

    # 获取 Agent
    result = await db.execute(
        select(Agent)
        .where(and_(Agent.id == aid, Agent.user_id == current_user.id))
        .options(selectinload(Agent.knowledge_bindings))
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 创建引擎并执行
    engine = AgentEngine(agent, agent.knowledge_bindings)
    chat_result = await engine.chat(data.message)

    # 创建会话记录
    thread_id = chat_result["thread_id"]
    session = AgentSession(
        agent_id=agent.id,
        user_id=current_user.id,
        thread_id=thread_id,
        title=data.message[:50] if len(data.message) > 50 else data.message,
        messages=[
            {"role": "user", "content": data.message},
            {"role": "assistant", "content": chat_result["response"]},
        ],
        message_count=2,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return ChatResponse(
        session_id=str(session.id),
        response=chat_result["response"],
        sources=[SourceReference(**s) for s in chat_result.get("sources", [])],
        tool_calls=[ToolCall(**tc) for tc in chat_result.get("tool_calls", [])],
        created_at=session.created_at,
    )


@router.post("/{agent_id}/sessions/{session_id}/chat", response_model=ChatResponse)
async def continue_agent_chat(
    agent_id: str,
    session_id: str,
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """继续对话"""
    try:
        aid = uuid.UUID(agent_id)
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid id format")

    # 获取 Agent 和 Session
    agent_result = await db.execute(
        select(Agent)
        .where(and_(Agent.id == aid, Agent.user_id == current_user.id))
        .options(selectinload(Agent.knowledge_bindings))
    )
    agent = agent_result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    session_result = await db.execute(
        select(AgentSession)
        .where(and_(AgentSession.id == sid, AgentSession.agent_id == aid))
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 执行对话
    engine = AgentEngine(agent, agent.knowledge_bindings)
    chat_result = await engine.chat(data.message, session.thread_id)

    # 更新会话消息
    messages = session.messages or []
    messages.append({"role": "user", "content": data.message})
    messages.append({"role": "assistant", "content": chat_result["response"]})
    session.messages = messages
    session.message_count = len(messages)
    session.updated_at = dt.datetime.utcnow()

    await db.commit()

    return ChatResponse(
        session_id=str(session.id),
        response=chat_result["response"],
        sources=[SourceReference(**s) for s in chat_result.get("sources", [])],
        tool_calls=[ToolCall(**tc) for tc in chat_result.get("tool_calls", [])],
        created_at=session.updated_at,
    )


@router.get("/{agent_id}/sessions", response_model=List[SessionResponse])
async def list_agent_sessions(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取会话列表"""
    try:
        aid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent_id format")

    result = await db.execute(
        select(AgentSession)
        .where(AgentSession.agent_id == aid)
        .order_by(AgentSession.updated_at.desc())
        .limit(20)
    )
    sessions = result.scalars().all()

    return [
        SessionResponse(
            id=str(s.id),
            agent_id=str(s.agent_id),
            thread_id=s.thread_id,
            title=s.title,
            message_count=s.message_count,
            messages=[],  # 列表不返回完整消息
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]


@router.get("/{agent_id}/sessions/{session_id}", response_model=SessionResponse)
async def get_agent_session(
    agent_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取会话详情"""
    try:
        aid = uuid.UUID(agent_id)
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid id format")

    result = await db.execute(
        select(AgentSession)
        .where(and_(AgentSession.id == sid, AgentSession.agent_id == aid))
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


@router.delete("/{agent_id}/sessions/{session_id}")
async def delete_agent_session(
    agent_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除会话"""
    try:
        aid = uuid.UUID(agent_id)
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid id format")

    result = await db.execute(
        select(AgentSession)
        .where(and_(AgentSession.id == sid, AgentSession.agent_id == aid))
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.delete(session)
    await db.commit()

    return {"message": "Session deleted"}


# ============= Agent Chat API =============

@router.post("/chat")
async def agent_chat(
    message: str = Body(...),
    thread_id: str = Body(None),
    model: str = Body("gpt-4o-mini"),
    system_prompt: str = Body(None),
    tools: List[str] = Body(None),
    current_user: User = Depends(get_current_user),
):
    """Agent 对话

    Args:
        message: 用户消息
        thread_id: 线程 ID（可选，用于继续对话）
        model: 模型名称
        system_prompt: 系统提示
        tools: 工具列表

    Returns:
        Agent 响应
    """
    if not thread_id:
        thread_id = str(uuid.uuid4())

    result = await agent_service.run_conversation(
        thread_id=thread_id,
        user_message=message,
        model=model,
        system_prompt=system_prompt,
        tools=tools,
    )

    return result


@router.post("/chat/{thread_id}")
async def continue_chat(
    thread_id: str,
    message: str = Body(..., embed=True),
    model: str = Body("gpt-4o-mini"),
    current_user: User = Depends(get_current_user),
):
    """继续对话

    Args:
        thread_id: 线程 ID
        message: 用户消息
        model: 模型名称

    Returns:
        Agent 响应
    """
    result = await agent_service.continue_conversation(
        thread_id=thread_id,
        user_message=message,
        model=model,
    )

    return result


@router.get("/history/{thread_id}")
async def get_history(thread_id: str):
    """获取对话历史"""
    messages = await agent_service.get_conversation_history(thread_id)
    return {"thread_id": thread_id, "messages": messages}