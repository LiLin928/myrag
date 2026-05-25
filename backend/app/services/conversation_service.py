"""对话管理服务

管理对话记录的 CRUD 和消息存储
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.models.conversation import Conversation
from app.models.message import Message
from app.api.dependencies.permissions import is_admin


class ConversationService:
    """对话管理服务"""

    async def create_conversation(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: str = None,
        title: str = None,
        mode: str = "model",
        model: str = "gpt-4o-mini",
        config: dict = None,
        workflow_id: str = None,
        system_prompt_template_id: str = None,
        custom_system_prompt: str = None,
        greeting_enabled: bool = False,
        greeting_content: str = None,
    ) -> Conversation:
        """创建对话

        Args:
            db: 数据库会话
            user_id: 用户 ID
            project_id: 项目 ID（可选）
            title: 标题
            mode: 对话模式 (model/workflow)
            model: 模型名称
            config: 对话配置 (JSON)
            workflow_id: 工作流 ID（workflow 模式）
            system_prompt_template_id: 系统提示词模板 ID
            custom_system_prompt: 自定义系统提示词
            greeting_enabled: 是否启用开场白
            greeting_content: 开场白内容

        Returns:
            Conversation 实例
        """
        thread_id = str(uuid.uuid4())

        conversation = Conversation(
            user_id=user_id,
            project_id=project_id,
            title=title,
            thread_id=thread_id,
            mode=mode,
            model=model,
            config=config,
            workflow_id=workflow_id,
            system_prompt_template_id=system_prompt_template_id,
            custom_system_prompt=custom_system_prompt,
            greeting_enabled=greeting_enabled,
            greeting_content=greeting_content,
        )

        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

        return conversation

    async def add_message(
        self,
        db: AsyncSession,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: List = None,
        tool_call_id: str = None,
        tool_result: Dict = None,
        tokens: int = 0,
    ) -> Message:
        """添加消息

        Args:
            db: 数据库会话
            conversation_id: 对话 ID
            role: 角色（user/assistant/tool/system）
            content: 内容
            tool_calls: 工具调用
            tool_call_id: 工具调用 ID
            tool_result: 工具结果
            tokens: Token 数量

        Returns:
            Message 实例
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            tool_result=tool_result,
            tokens=tokens,
        )

        db.add(message)

        # 更新对话统计
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.message_count += 1
            conversation.total_tokens += tokens

        await db.commit()
        await db.refresh(message)

        return message

    async def get_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
    ) -> Optional[Conversation]:
        """获取对话"""
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_messages(
        self,
        db: AsyncSession,
        conversation_id: str,
    ) -> List[Message]:
        """获取对话消息"""
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        return result.scalars().all()

    async def list_conversations(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: str = None,
    ) -> List[Conversation]:
        """列出对话"""
        query = select(Conversation).where(Conversation.user_id == user_id)

        if project_id:
            query = query.where(Conversation.project_id == project_id)

        result = await db.execute(query.order_by(Conversation.updated_at.desc()))
        return result.scalars().all()

    async def list_conversations_with_permission(
        self,
        db: AsyncSession,
        current_user,
        skip: int = 0,
        limit: int = 10,
        include_all: bool = False,
    ) -> List[Conversation]:
        """根据权限列出对话

        Args:
            db: 数据库会话
            current_user: 当前用户
            skip: 跳过记录数
            limit: 返回记录数
            include_all: 是否查看所有用户的对话（仅 admin 有效）

        Returns:
            Conversation 列表
        """
        # 检查用户是否为管理员
        is_user_admin = await is_admin(current_user)

        # 构建查询
        query = select(Conversation)

        # 普通用户只能看自己的对话
        # admin 默认看自己的，include_all=True 可看全部
        if not is_user_admin or not include_all:
            query = query.where(Conversation.user_id == current_user.id)

        # 添加分页和排序
        query = query.order_by(Conversation.updated_at.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    async def delete_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
    ):
        """删除对话"""
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        conversation = result.scalar_one_or_none()

        if conversation:
            await db.delete(conversation)
            await db.commit()

    async def get_by_thread_id(
        self,
        db: AsyncSession,
        thread_id: str,
    ) -> Optional[Conversation]:
        """按 thread_id 获取对话"""
        result = await db.execute(
            select(Conversation).where(Conversation.thread_id == thread_id)
        )
        return result.scalar_one_or_none()


# 全局服务实例
conversation_service = ConversationService()