"""对话管理 API 路由"""

from typing import Optional, List
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.permissions import is_admin
from app.models.user import User
from app.models.conversation import Conversation
from app.models.conversation_config_history import ConversationConfigHistory
from app.models.knowledge_base import KnowledgeBase
from app.models.system_prompt_template import SystemPromptTemplate
from app.models.message import Message
from app.workflow.models.workflow import Workflow
from app.services.conversation_service import conversation_service
from app.services.agent_service import agent_service
from app.db import get_db

router = APIRouter(prefix="/conversations", tags=["conversations"])


# ============ Pydantic Schemas ============

class KnowledgeBaseConfig(BaseModel):
    """知识库检索配置"""
    top_k: int = Field(default=10, ge=1, le=100, description="返回结果数量")
    threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="相似度阈值")
    search_type: str = Field(default="hybrid", description="检索类型: vector/keyword/hybrid")


class ConversationConfig(BaseModel):
    """对话配置"""
    knowledge_base_ids: List[str] = Field(default=[], description="关联的知识库 ID 列表")
    knowledge_base_config: Optional[KnowledgeBaseConfig] = Field(None, description="知识库检索配置")
    tools_enabled: bool = Field(default=False, description="是否启用工具")
    tool_ids: List[str] = Field(default=[], description="启用的工具 ID 列表")
    skills_enabled: bool = Field(default=False, description="是否启用技能")
    skill_ids: List[str] = Field(default=[], description="启用的技能 ID 列表")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="模型温度")
    max_tokens: int = Field(default=2000, ge=1, le=10000, description="最大输出 Token 数")


class ConversationCreate(BaseModel):
    """创建对话请求"""
    title: Optional[str] = Field(None, max_length=255, description="对话标题")
    mode: str = Field(default="model", description="对话模式: model/workflow")
    model: Optional[str] = Field(None, max_length=64, description="模型名称")
    config: Optional[ConversationConfig] = Field(None, description="对话配置")
    workflow_id: Optional[str] = Field(None, description="工作流 ID（workflow 模式必填）")
    system_prompt_template_id: Optional[str] = Field(None, description="系统提示词模板 ID")
    custom_system_prompt: Optional[str] = Field(None, description="自定义系统提示词")
    greeting_enabled: bool = Field(default=False, description="是否启用开场白")
    greeting_content: Optional[str] = Field(None, description="开场白内容")
    project_id: Optional[str] = Field(None, description="项目 ID")


class ConfigUpdate(BaseModel):
    """更新配置请求"""
    config: Optional[ConversationConfig] = Field(None, description="对话配置")
    system_prompt_template_id: Optional[str] = Field(None, description="系统提示词模板 ID")
    custom_system_prompt: Optional[str] = Field(None, description="自定义系统提示词")
    greeting_enabled: Optional[bool] = Field(None, description="是否启用开场白")
    greeting_content: Optional[str] = Field(None, description="开场白内容")


class ConfigResponse(BaseModel):
    """配置响应"""
    mode: str
    config: Optional[dict] = None
    model: Optional[str] = None
    workflow_id: Optional[str] = None
    system_prompt_template_id: Optional[str] = None
    custom_system_prompt: Optional[str] = None
    greeting_enabled: bool
    greeting_content: Optional[str] = None


class ConfigHistoryResponse(BaseModel):
    """配置历史响应"""
    id: str
    conversation_id: str
    old_config: Optional[dict] = None
    new_config: Optional[dict] = None
    old_system_prompt_template_id: Optional[str] = None
    new_system_prompt_template_id: Optional[str] = None
    changed_by: str
    changed_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """对话响应"""
    id: str
    thread_id: str
    title: Optional[str]
    mode: str
    model: Optional[str]
    config: Optional[dict]
    workflow_id: Optional[str]
    system_prompt_template_id: Optional[str]
    custom_system_prompt: Optional[str]
    greeting_enabled: bool
    greeting_content: Optional[str]
    message_count: int
    total_tokens: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Helper Functions ============

def validate_uuid(uuid_str: str) -> bool:
    """验证 UUID 格式"""
    try:
        UUID(uuid_str)
        return True
    except ValueError:
        return False


async def validate_workflow(db: AsyncSession, workflow_id: str) -> Workflow:
    """验证工作流存在"""
    if not validate_uuid(workflow_id):
        raise HTTPException(status_code=400, detail="无效的工作流 ID 格式")

    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")

    return workflow


async def validate_knowledge_bases(db: AsyncSession, kb_ids: List[str]) -> None:
    """验证知识库存在"""
    for kb_id in kb_ids:
        if not validate_uuid(kb_id):
            raise HTTPException(status_code=400, detail=f"无效的知识库 ID 格式: {kb_id}")

        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        kb = result.scalar_one_or_none()

        if not kb:
            raise HTTPException(status_code=404, detail=f"知识库不存在: {kb_id}")


async def validate_conversation_id(conversation_id: str) -> None:
    """验证对话 ID 格式"""
    if not validate_uuid(conversation_id):
        raise HTTPException(status_code=400, detail="无效的对话 ID 格式")


async def validate_system_prompt_template(db: AsyncSession, template_id: str) -> SystemPromptTemplate:
    """验证系统提示词模板存在"""
    if not validate_uuid(template_id):
        raise HTTPException(status_code=400, detail="无效的模板 ID 格式")

    result = await db.execute(
        select(SystemPromptTemplate).where(SystemPromptTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="系统提示词模板不存在")

    return template


def conversation_to_response(conversation: Conversation) -> dict:
    """将对话模型转换为响应字典"""
    return {
        "id": str(conversation.id),
        "thread_id": conversation.thread_id,
        "title": conversation.title,
        "mode": conversation.mode or "model",
        "model": conversation.model,
        "config": conversation.config,
        "workflow_id": str(conversation.workflow_id) if conversation.workflow_id else None,
        "system_prompt_template_id": str(conversation.system_prompt_template_id) if conversation.system_prompt_template_id else None,
        "custom_system_prompt": conversation.custom_system_prompt,
        "greeting_enabled": conversation.greeting_enabled or False,
        "greeting_content": conversation.greeting_content,
        "message_count": conversation.message_count or 0,
        "total_tokens": conversation.total_tokens or 0,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }


# ============ API Endpoints ============

@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建对话

    支持两种模式:
    - model: 使用大模型直接对话
    - workflow: 使用工作流进行对话
    """
    # 验证模式
    if data.mode not in ["model", "workflow"]:
        raise HTTPException(status_code=400, detail="模式必须是 'model' 或 'workflow'")

    # 工作流模式验证
    if data.mode == "workflow":
        if not data.workflow_id:
            raise HTTPException(status_code=400, detail="workflow 模式需要指定 workflow_id")
        await validate_workflow(db, data.workflow_id)

    # 模型模式验证知识库
    if data.mode == "model" and data.config and data.config.knowledge_base_ids:
        await validate_knowledge_bases(db, data.config.knowledge_base_ids)

    # 创建对话
    conversation = await conversation_service.create_conversation(
        db=db,
        user_id=str(current_user.id),
        project_id=data.project_id,
        title=data.title,
        mode=data.mode,
        model=data.model,
        config=data.config.model_dump() if data.config else None,
        workflow_id=data.workflow_id,
        system_prompt_template_id=data.system_prompt_template_id,
        custom_system_prompt=data.custom_system_prompt,
        greeting_enabled=data.greeting_enabled,
        greeting_content=data.greeting_content,
    )

    return conversation_to_response(conversation)


@router.get("/")
async def list_conversations(
    project_id: str = None,
    all_users: bool = Query(False, description="查看所有用户的对话（仅 admin/superuser 可用）"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出对话

    Args:
        project_id: 项目 ID（可选）
        all_users: 是否查看所有用户的对话（仅 admin/superuser 可用）
        skip: 跳过记录数
        limit: 返回记录数
        db: 数据库会话
        current_user: 当前用户

    Returns:
        对话列表
    """
    # 权限检查：只有 admin/superuser 才能使用 all_users=True
    if all_users:
        user_is_admin = await is_admin(current_user)
        if not user_is_admin:
            raise HTTPException(
                status_code=403,
                detail="权限不足：只有管理员才能查看所有用户的对话"
            )

    # 使用带权限过滤的查询方法
    conversations = await conversation_service.list_conversations_with_permission(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        include_all=all_users,
    )

    # 构建返回数据
    result = []
    for c in conversations:
        item = {
            "id": str(c.id),
            "title": c.title,
            "mode": c.mode or "model",
            "model": c.model,
            "message_count": c.message_count,
            "updated_at": c.updated_at,
        }
        # 如果是查看所有用户的对话，返回 user_id
        if all_users:
            item["user_id"] = c.user_id
        result.append(item)

    return result


@router.get("/{conversation_id}/", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取对话详情"""
    conversation = await conversation_service.get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=str(current_user.id),
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation_to_response(conversation)


@router.put("/{conversation_id}/config", response_model=ConfigResponse)
async def update_config(
    conversation_id: str,
    data: ConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新对话配置

    更新对话的配置信息，并记录变更历史
    """
    # 验证对话 ID 格式
    await validate_conversation_id(conversation_id)

    # 获取对话
    conversation = await conversation_service.get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=str(current_user.id),
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    # 验证知识库（如果配置中有）
    if data.config and data.config.knowledge_base_ids:
        await validate_knowledge_bases(db, data.config.knowledge_base_ids)

    # 验证系统提示词模板（如果提供）
    if data.system_prompt_template_id:
        await validate_system_prompt_template(db, data.system_prompt_template_id)

    # 记录变更历史
    old_config = conversation.config
    old_template_id = str(conversation.system_prompt_template_id) if conversation.system_prompt_template_id else None

    # 更新配置
    if data.config is not None:
        conversation.config = data.config.model_dump()
    if data.system_prompt_template_id is not None:
        conversation.system_prompt_template_id = data.system_prompt_template_id
    if data.custom_system_prompt is not None:
        conversation.custom_system_prompt = data.custom_system_prompt
    if data.greeting_enabled is not None:
        conversation.greeting_enabled = data.greeting_enabled
    if data.greeting_content is not None:
        conversation.greeting_content = data.greeting_content

    # 创建变更历史记录
    new_config = conversation.config
    new_template_id = str(conversation.system_prompt_template_id) if conversation.system_prompt_template_id else None

    # 只有在配置确实变更时才记录历史
    if old_config != new_config or old_template_id != new_template_id:
        history = ConversationConfigHistory(
            conversation_id=conversation_id,
            old_config=old_config,
            new_config=new_config,
            old_system_prompt_template_id=old_template_id,
            new_system_prompt_template_id=new_template_id,
            changed_by=str(current_user.id),
        )
        db.add(history)

    await db.commit()
    await db.refresh(conversation)

    return ConfigResponse(
        mode=conversation.mode or "model",
        config=conversation.config,
        model=conversation.model,
        workflow_id=str(conversation.workflow_id) if conversation.workflow_id else None,
        system_prompt_template_id=str(conversation.system_prompt_template_id) if conversation.system_prompt_template_id else None,
        custom_system_prompt=conversation.custom_system_prompt,
        greeting_enabled=conversation.greeting_enabled or False,
        greeting_content=conversation.greeting_content,
    )


@router.get("/{conversation_id}/config", response_model=ConfigResponse)
async def get_config(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取对话当前配置"""
    await validate_conversation_id(conversation_id)

    conversation = await conversation_service.get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=str(current_user.id),
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    return ConfigResponse(
        mode=conversation.mode or "model",
        config=conversation.config,
        model=conversation.model,
        workflow_id=str(conversation.workflow_id) if conversation.workflow_id else None,
        system_prompt_template_id=str(conversation.system_prompt_template_id) if conversation.system_prompt_template_id else None,
        custom_system_prompt=conversation.custom_system_prompt,
        greeting_enabled=conversation.greeting_enabled or False,
        greeting_content=conversation.greeting_content,
    )


@router.get("/{conversation_id}/config-history", response_model=List[ConfigHistoryResponse])
async def get_config_history(
    conversation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取对话配置变更历史"""
    await validate_conversation_id(conversation_id)

    # 验证对话存在且有权限访问
    conversation = await conversation_service.get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=str(current_user.id),
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    # 查询配置历史
    result = await db.execute(
        select(ConversationConfigHistory)
        .where(ConversationConfigHistory.conversation_id == conversation_id)
        .order_by(ConversationConfigHistory.changed_at.desc())
        .offset(skip)
        .limit(limit)
    )
    histories = result.scalars().all()

    return [
        ConfigHistoryResponse(
            id=str(h.id),
            conversation_id=str(h.conversation_id),
            old_config=h.old_config,
            new_config=h.new_config,
            old_system_prompt_template_id=h.old_system_prompt_template_id,
            new_system_prompt_template_id=h.new_system_prompt_template_id,
            changed_by=str(h.changed_by),
            changed_at=h.changed_at,
        )
        for h in histories
    ]


class GreetingMessageResponse(BaseModel):
    """开场白消息响应"""
    id: str
    conversation_id: str
    role: str
    content: str
    tokens: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/{conversation_id}/send-greeting", response_model=GreetingMessageResponse)
async def send_greeting(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发送开场白

    发送对话的开场白消息（仅当 greeting_enabled=True 且 greeting_sent=False 时可发送）
    """
    # 1. 验证对话 ID 格式
    await validate_conversation_id(conversation_id)

    # 2. 获取对话并检查用户权限
    conversation = await conversation_service.get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=str(current_user.id),
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    # 3. 检查是否启用开场白
    if not conversation.greeting_enabled:
        raise HTTPException(status_code=400, detail="该对话未启用开场白功能")

    # 4. 检查是否已发送过开场白
    if conversation.greeting_sent:
        raise HTTPException(status_code=400, detail="开场白已发送，不可重复发送")

    # 5. 检查是否有开场白内容
    if not conversation.greeting_content:
        raise HTTPException(status_code=400, detail="未设置开场白内容")

    # 6. 创建消息
    message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=conversation.greeting_content,
        tokens=0,
    )
    db.add(message)

    # 7. 更新对话状态
    conversation.greeting_sent = True
    conversation.message_count = (conversation.message_count or 0) + 1

    # 8. 提交更改
    await db.commit()
    await db.refresh(message)

    # 9. 返回消息详情
    return GreetingMessageResponse(
        id=str(message.id),
        conversation_id=str(message.conversation_id),
        role=message.role,
        content=message.content,
        tokens=message.tokens or 0,
        created_at=message.created_at,
    )


@router.post("/{conversation_id}/messages/")
async def send_message(
    conversation_id: str,
    message: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发送消息"""
    # 获取对话
    conversation = await conversation_service.get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=str(current_user.id),
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # 添加用户消息
    await conversation_service.add_message(
        db=db,
        conversation_id=conversation_id,
        role="user",
        content=message,
    )

    # 调用 Agent
    result = await agent_service.continue_conversation(
        thread_id=conversation.thread_id,
        user_message=message,
        model=conversation.model,
        system_prompt=conversation.system_prompt,
    )

    # 添加助手消息
    await conversation_service.add_message(
        db=db,
        conversation_id=conversation_id,
        role="assistant",
        content=result["response"],
    )

    return {"response": result["response"]}


@router.get("/{conversation_id}/messages/")
async def get_messages(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取对话消息"""
    messages = await conversation_service.get_messages(
        db=db,
        conversation_id=conversation_id,
    )

    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "tool_calls": m.tool_calls,
            "tokens": m.tokens,
            "created_at": m.created_at,
        }
        for m in messages
    ]


@router.delete("/{conversation_id}/")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除对话"""
    await conversation_service.delete_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=str(current_user.id),
    )

    return {"deleted": conversation_id}