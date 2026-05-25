"""Agent 会话数据模型"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import Base


class AgentSession(Base):
    """Agent 会话表"""

    __tablename__ = "agent_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # LangGraph thread ID
    thread_id = Column(String(64), nullable=False, unique=True)

    # 会话信息
    title = Column(String(200), nullable=True)
    messages = Column(JSON, nullable=True)

    # 统计
    message_count = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    agent = relationship("Agent", back_populates="sessions")
    user = relationship("User", backref="agent_sessions")

    def __repr__(self):
        return f"<AgentSession(id={self.id}, thread_id={self.thread_id})>"