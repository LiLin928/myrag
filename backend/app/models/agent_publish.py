"""Agent 发布数据模型"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import Base


class PublishType:
    """发布类型常量"""
    EMBED = "embed"
    LINK = "link"
    API = "api"


class PublishStatus:
    """发布状态常量"""
    ACTIVE = "active"
    DISABLED = "disabled"


class AgentPublish(Base):
    """Agent 发布表"""

    __tablename__ = "agent_publishes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)

    # 发布类型
    publish_type = Column(String(20), nullable=False)

    # 发布内容
    embed_code = Column(Text, nullable=True)
    link_url = Column(String(255), nullable=True)
    api_key = Column(String(64), nullable=True)

    # 配置
    config = Column(Text, nullable=True)

    # 状态
    status = Column(String(20), default="active")

    # 统计
    access_count = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    agent = relationship("Agent", back_populates="publishes")

    def __repr__(self):
        return f"<AgentPublish(id={self.id}, publish_type={self.publish_type})>"