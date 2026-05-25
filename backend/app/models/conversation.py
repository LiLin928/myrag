"""对话数据模型"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import Base


class Conversation(Base):
    """对话表"""

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True, index=True)

    # 基本信息
    title = Column(String(255), nullable=True)  # 对话标题（自动生成或用户设置）
    thread_id = Column(String(64), nullable=False, unique=True)  # LangGraph thread ID

    # 对话模式
    mode = Column(String(20), default="model")  # model/workflow

    # 配置
    model = Column(String(64), default="gpt-4o-mini")
    system_prompt = Column(Text, nullable=True)
    temperature = Column(JSON, nullable=True)

    # 模型模式配置 (JSON)
    config = Column(JSON, nullable=True)

    # 工作流模式配置
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=True)

    # 系统提示词配置
    system_prompt_template_id = Column(String(36), ForeignKey("system_prompt_templates.id"), nullable=True)
    custom_system_prompt = Column(Text, nullable=True)

    # 动态开场白
    greeting_enabled = Column(Boolean, default=False)
    greeting_content = Column(Text, nullable=True)
    greeting_sent = Column(Boolean, default=False)

    # 统计
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # 状态
    is_active = Column(Boolean, default=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    workflow = relationship("Workflow", foreign_keys=[workflow_id])
    system_prompt_template = relationship("SystemPromptTemplate", foreign_keys=[system_prompt_template_id])

    def __repr__(self):
        return f"<Conversation(id={self.id}, title={self.title})>"