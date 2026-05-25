"""文档数据模型

定义文档处理相关数据表：
- Document: 文档元数据
- DocumentChunk: 文档分块（条款级）
- DocumentProcessing: 处理状态追踪
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

from pgvector.sqlalchemy import Vector

from app.models.base import Base, BaseModel


class DocumentStatus(str, enum.Enum):
    """文档处理状态"""
    PENDING = "pending"          # 待处理
    PARSING = "parsing"          # 正在解析
    PARSED = "parsed"            # 解析完成
    VECTORIZING = "vectorizing"  # 正在向量化（新增）
    INDEXING = "indexing"        # 正在索引
    INDEXED = "indexed"          # 索引完成（等价于 VECTORIZED）
    COMPLETED = "completed"      # 处理完成（最终状态）
    COMPILED = "compiled"        # 知识预编译完成
    FAILED = "failed"            # 处理失败

    # 状态别名（向后兼容）
    @classmethod
    def _missing_(cls, value):
        # INDEXED 和 COMPLETED 是等价状态
        if value == "vectorized":
            return cls.INDEXED
        if value == "completed":
            return cls.COMPLETED
        return None


class DocumentType(str, enum.Enum):
    """文档类型"""
    PDF = "pdf"
    WORD = "word"
    MARKDOWN = "markdown"
    TEXT = "text"
    HTML = "html"
    IMAGE = "image"


class Document(Base):
    """文档元数据表"""

    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True, index=True)
    knowledge_base_id = Column(String(36), ForeignKey("knowledge_bases.id"), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 文件信息
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)  # MinIO 存储路径
    file_type = Column(String(20), nullable=False)  # 使用 String 类型存储枚举值
    file_size = Column(Integer, nullable=False)  # bytes

    # 处理状态
    status = Column(String(20), default="pending", index=True)  # 使用 String 类型存储枚举值
    processing_job_id = Column(String(64), nullable=True)  # ARQ 任务 ID

    # 解析结果
    parsed_content_path = Column(String(512), nullable=True)  # 解析输出路径
    content_blocks_count = Column(Integer, default=0)

    # 分块配置
    chunk_strategy = Column(String(20), default="auto")  # auto/structured/semantic/fixed
    chunk_size = Column(Integer, default=800)
    chunk_overlap = Column(Integer, default=100)
    chunk_count = Column(Integer, default=0)

    # 向量化配置
    enable_vectorization = Column(Boolean, default=True)
    embedding_model = Column(String(64), default="text-embedding-3-small")
    vector_dimension = Column(Integer, default=1536)
    vectorized_count = Column(Integer, default=0)

    # 文档处理进度
    processing_progress = Column(Integer, default=0)  # 0-100
    processing_message = Column(String(255), nullable=True)

    # 元数据
    doc_metadata = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    # 关系
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"


class DocumentChunk(Base):
    """文档分块表（条款级）"""

    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True, index=True)
    knowledge_base_id = Column(String(36), ForeignKey("knowledge_bases.id"), nullable=True, index=True)

    # 条款信息
    clause_id = Column(String(64), nullable=False, index=True)  # 条款唯一标识
    clause_type = Column(String(32), nullable=True, index=True)  # 条款类型
    clause_title = Column(String(255), nullable=True)
    parent_clause_id = Column(String(64), nullable=True)  # 父条款 ID（层级关系）

    # 内容
    content = Column(Text, nullable=False)
    # content_tsv 由数据库触发器自动填充，不需要在模型中定义
    # content_tsv = Column(Text, nullable=True)  # 移除：这会与触发器冲突
    page_number = Column(Integer, default=1)

    # 向量信息（PGVector）
    embedding_vector = Column(Vector(1536), nullable=True)  # 1536 维向量
    embedding_model = Column(String(64), nullable=True)

    # 元数据
    chunk_metadata = Column(JSON, nullable=True)

    # 三级元数据结构
    # 文档基础信息（自动生成，只读）
    document_type = Column(String(20), nullable=True)  # PDF/Word/Markdown
    source_filename = Column(String(255), nullable=True)

    # 文档结构信息（自动生成，只读）
    section_title = Column(String(255), nullable=True)
    section_level = Column(Integer, default=1)
    position_type = Column(String(32), nullable=True)  # header/body/table/footer

    # 用户自定义元数据（JSON）
    user_metadata = Column(JSON, nullable=True, default={})
    # 结构: {
    #   "user_tags": ["重要", "技术"],
    #   "category": "核心内容",
    #   "note": "备注",
    #   "custom_fields": {"业务领域": "产品"}
    # }

    # 内容统计
    content_length = Column(Integer, default=0)

    # 向量化时间
    embedding_created_at = Column(DateTime, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    document = relationship("Document", back_populates="chunks")

    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, clause_id={self.clause_id})>"


class DocumentProcessing(Base):
    """文档处理状态追踪表"""

    __tablename__ = "document_processing"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    # ARQ 任务信息
    job_id = Column(String(64), nullable=False, index=True)
    task_type = Column(String(32), nullable=False)  # parse/vectorize/compile

    # 进度
    stage = Column(String(32), nullable=False)
    progress = Column(Integer, default=0)  # 0-100
    message = Column(Text, nullable=True)

    # 结果
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    # 时间戳
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<DocumentProcessing(id={self.id}, job_id={self.job_id}, stage={self.stage})>"