"""知识库数据模型"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import Base


class KnowledgeBase(Base):
    """知识库表"""

    __tablename__ = "knowledge_bases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)

    # 基本信息
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # 配置
    embedding_model = Column(String(64), default="text-embedding-3-small")
    vector_dimension = Column(Integer, default=1536)

    # 分块配置
    chunk_strategy = Column(String(20), default="auto")  # auto, semantic, fixed, recursive
    chunk_size = Column(Integer, default=800)
    chunk_overlap = Column(Integer, default=100)

    # Rerank 配置
    rerank_model = Column(String(64), nullable=True)
    rerank_enabled = Column(Boolean, default=False)
    rerank_top_n = Column(Integer, default=10)

    # 检索配置
    retrieval_method = Column(String(20), default="hybrid")  # vector, keyword, hybrid
    retrieval_top_k = Column(Integer, default=10)
    similarity_threshold = Column(Float, default=0.5)

    # 混合检索权重
    vector_weight = Column(Float, default=0.7)
    keyword_weight = Column(Float, default=0.3)

    # 统计
    document_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    vectorized_count = Column(Integer, default=0)

    # 元数据
    kb_metadata = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    user = relationship("User", backref="knowledge_bases")
    documents = relationship("Document", backref="knowledge_base", foreign_keys="[Document.knowledge_base_id]")

    def __repr__(self):
        return f"<KnowledgeBase(id={self.id}, name={self.name})>"