"""Document Pydantic Schema"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DocumentStatusEnum(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    PARSED = "parsed"
    CHUNKING = "chunking"
    CHUNKED = "chunked"
    INDEXING = "indexing"
    INDEXED = "indexed"
    COMPILED = "compiled"
    FAILED = "failed"


class ChunkStrategyEnum(str, Enum):
    AUTO = "auto"
    STRUCTURED = "structured"
    SEMANTIC = "semantic"
    FIXED = "fixed"


class DocumentUploadRequest(BaseModel):
    """文档上传请求参数"""
    chunk_strategy: ChunkStrategyEnum = ChunkStrategyEnum.AUTO
    enable_vectorization: bool = True


class DocumentStatusResponse(BaseModel):
    """文档处理状态响应"""
    document_id: str
    status: DocumentStatusEnum
    progress: int = Field(ge=0, le=100)
    message: Optional[str] = None
    chunk_count: int = 0
    vectorized_count: int = 0
    websocket_channel: Optional[str] = None


class DocumentDetailResponse(BaseModel):
    """文档详情响应"""
    id: str
    filename: str
    file_type: str
    file_size: int
    status: DocumentStatusEnum
    chunk_strategy: ChunkStrategyEnum
    chunk_count: int
    vectorized_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    total: int
    documents: List[DocumentDetailResponse]