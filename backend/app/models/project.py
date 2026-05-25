"""项目数据模型

项目是组织文档、知识库和对话的核心单元
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import Base


class Project(Base):
    """项目表"""

    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 基本信息
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # 配置
    embedding_model = Column(String(64), default="text-embedding-3-small")
    vector_dimension = Column(Integer, default=1536)

    # 统计
    document_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)

    # 元数据
    project_metadata = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    documents = relationship("Document", backref="project", foreign_keys="[Document.project_id]")
    knowledge_base = relationship("KnowledgeBase", backref="project", uselist=False, foreign_keys="[KnowledgeBase.project_id]")
    conversations = relationship("Conversation", backref="project", foreign_keys="[Conversation.project_id]")

    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name})>"