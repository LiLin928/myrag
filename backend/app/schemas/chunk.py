"""Chunk Pydantic Schema"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.schemas.metadata import MetadataResponse


class ChunkMetadata(BaseModel):
    """分块元数据结构"""
    # 文档基础信息（只读）
    document_type: Optional[str] = None
    source_filename: Optional[str] = None

    # 文档结构信息（只读）
    section_title: Optional[str] = None
    section_level: Optional[int] = None
    position_type: Optional[str] = None

    # 用户自定义元数据（可编辑）
    user_tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    note: Optional[str] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class ChunkBase(BaseModel):
    """分块基础信息"""
    id: str
    document_id: str
    clause_id: str
    clause_type: Optional[str] = None
    clause_title: Optional[str] = None
    content: str
    page_number: int = 1


class ChunkDetail(ChunkBase):
    """分块详细信息"""
    content_length: int = 0
    metadata: ChunkMetadata = ChunkMetadata()
    has_embedding: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None


class ChunkListResponse(BaseModel):
    """分块列表响应"""
    total: int
    page: int
    page_size: int
    chunks: List[ChunkDetail]


class ChunkMetadataUpdate(BaseModel):
    """分块元数据更新请求"""
    user_tags: Optional[List[str]] = None
    category: Optional[str] = None
    note: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class ChunkContentUpdate(BaseModel):
    """分块内容更新请求"""
    content: str


class ChunkDetailWithMetadata(ChunkBase):
    """分块详细信息（含继承元数据）"""
    content_length: int = 0
    metadata: MetadataResponse = Field(default_factory=MetadataResponse)
    has_embedding: bool = False
    created_at: datetime


class ChunkListWithMetadataResponse(BaseModel):
    """分块列表响应（含继承元数据）"""
    total: int
    page: int
    page_size: int
    chunks: List[ChunkDetailWithMetadata]