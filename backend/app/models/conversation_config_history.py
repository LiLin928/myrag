"""对话配置变更历史模型"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import Base


class ConversationConfigHistory(Base):
    """对话配置变更历史表"""
    __tablename__ = "conversation_config_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)

    # 变更内容
    old_config = Column(JSON, nullable=True)
    new_config = Column(JSON, nullable=True)
    old_system_prompt_template_id = Column(String(36), nullable=True)
    new_system_prompt_template_id = Column(String(36), nullable=True)

    # 变更信息
    changed_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    conversation = relationship("Conversation")
    user = relationship("User")

    def __repr__(self):
        return f"<ConversationConfigHistory(id={self.id}, conversation_id={self.conversation_id})>"