"""模型配置数据模型"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

from app.models.base import Base


class ModelType(str, enum.Enum):
    """模型类型"""
    LLM = "llm"
    EMBEDDING = "embedding"
    RERANK = "rerank"


class ModelConfig(Base):
    """模型配置表"""

    __tablename__ = "model_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 基本信息
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False, index=True)  # 使用 VARCHAR 存储枚举值
    provider = Column(String(50), nullable=False)

    # API 配置
    api_base = Column(String(255), nullable=False)
    api_key = Column(String(255), nullable=False)  # 加密存储
    model_name = Column(String(100), nullable=False)

    # LLM 类型参数
    context_length = Column(Integer, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    temperature = Column(Integer, nullable=True)  # 存储为整数，使用时除以 10

    # Embedding 类型参数
    dimension = Column(Integer, nullable=True)
    batch_size = Column(Integer, nullable=True)

    # Rerank 类型参数
    top_k = Column(Integer, nullable=True)

    # 通用参数
    timeout = Column(Integer, default=30)
    extra_config = Column(JSON, nullable=True)

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)

    # 创建者
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    creator = relationship("User", foreign_keys=[created_by])
    users = relationship("User", secondary="user_model_configs", back_populates="bound_model_configs", lazy='selectin')

    def __repr__(self):
        return f"<ModelConfig(id={self.id}, name={self.name}, type={self.type})>"