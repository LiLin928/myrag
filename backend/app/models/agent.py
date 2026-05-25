"""Agent 数据模型"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import Base


class Agent(Base):
    """智能体主表"""

    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 基本信息
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # 模型配置
    model_id = Column(String(36), ForeignKey("model_configs.id"), nullable=False, index=True)

    # 系统提示词
    system_prompt = Column(Text, nullable=True)

    # 开关配置
    use_knowledge = Column(Boolean, default=False)
    use_tools = Column(Boolean, default=False)
    use_skills = Column(Boolean, default=False)

    # 高级检索配置
    search_type = Column(String(20), default="hybrid")  # semantic/keyword/hybrid
    top_k = Column(Integer, default=5)
    score_threshold = Column(Integer, default=50)  # 存储为整数（百分比），使用时除以 100

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    user = relationship("User", backref="agents")
    model = relationship("ModelConfig", foreign_keys=[model_id])
    knowledge_bindings = relationship("AgentKnowledgeBinding", back_populates="agent", cascade="all, delete-orphan")
    tool_bindings = relationship("AgentToolBinding", back_populates="agent", cascade="all, delete-orphan")
    skill_bindings = relationship("AgentSkillBinding", back_populates="agent", cascade="all, delete-orphan")
    sessions = relationship("AgentSession", back_populates="agent", cascade="all, delete-orphan")
    publishes = relationship("AgentPublish", back_populates="agent", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Agent(id={self.id}, name={self.name})>"