"""Agent 发布 Schema"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class PublishRequest(BaseModel):
    """发布请求"""
    publish_type: str = Field(..., pattern="^(embed|link|api)$")
    config: Optional[Dict[str, Any]] = None  # 主题色、位置、标题等


class PublishResponse(BaseModel):
    """发布响应"""
    id: str
    agent_id: str
    publish_type: str
    embed_code: Optional[str]
    link_url: Optional[str]
    api_key: Optional[str]
    status: str
    access_count: int
    created_at: datetime


class PublishListResponse(BaseModel):
    """发布列表响应"""
    id: str
    agent_name: str
    publish_type: str
    status: str
    access_count: int
    created_at: datetime


class PublicChatRequest(BaseModel):
    """公开对话请求"""
    message: str = Field(..., min_length=1)
    thread_id: Optional[str] = None