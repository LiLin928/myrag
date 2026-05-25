"""系统提示词模板模型"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import Base


class SystemPromptTemplate(Base):
    """系统提示词模板表"""
    __tablename__ = "system_prompt_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # 基本信息
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    category = Column(String(50), nullable=True, index=True)

    # 状态
    is_public = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    user = relationship("User")

    def __repr__(self):
        return f"<SystemPromptTemplate(id={self.id}, name={self.name})>"