"""Agent 关联表模型"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import Base


class AgentKnowledgeBinding(Base):
    """Agent 知识库关联表"""

    __tablename__ = "agent_knowledge_bindings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    knowledge_base_id = Column(String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)

    # 检索配置
    search_type = Column(String(20), default="hybrid")
    top_k = Column(Integer, default=5)
    score_threshold = Column(Float, default=0.5)
    priority = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    agent = relationship("Agent", back_populates="knowledge_bindings")
    knowledge_base = relationship("KnowledgeBase")


class AgentToolBinding(Base):
    """Agent 工具关联表"""

    __tablename__ = "agent_tool_bindings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_name = Column(String(50), nullable=False)  # 内置工具标识

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    agent = relationship("Agent", back_populates="tool_bindings")


class AgentSkillBinding(Base):
    """Agent Skills 关联表"""

    __tablename__ = "agent_skill_bindings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(String(36), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    agent = relationship("Agent", back_populates="skill_bindings")
    skill = relationship("Skill")