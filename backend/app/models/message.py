"""消息数据模型"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import Base


class Message(Base):
    """消息表"""

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)

    # 消息内容
    role = Column(String(20), nullable=False)  # user/assistant/tool/system
    content = Column(Text, nullable=True)

    # 工具调用（如有）
    tool_calls = Column(JSON, nullable=True)  # [{"name": "...", "args": {...}}]
    tool_call_id = Column(String(64), nullable=True)
    tool_result = Column(JSON, nullable=True)

    # Token 统计
    tokens = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role})>"