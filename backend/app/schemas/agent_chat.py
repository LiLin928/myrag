"""Agent 对话 Schema"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., min_length=1)
    use_knowledge: bool = True
    use_tools: bool = True
    session_id: Optional[str] = None


class SourceReference(BaseModel):
    """引用来源"""
    doc_name: str
    chunk: str
    score: float


class ToolCall(BaseModel):
    """工具调用记录"""
    tool: str
    args: Dict[str, Any]
    result: Optional[str]


class ChatResponse(BaseModel):
    """对话响应"""
    session_id: str
    response: str
    sources: List[SourceReference] = []
    tool_calls: List[ToolCall] = []
    created_at: datetime


class SessionMessage(BaseModel):
    """会话消息"""
    role: str
    content: str
    sources: List[SourceReference] = []
    tool_calls: List[ToolCall] = []
    created_at: datetime


class SessionResponse(BaseModel):
    """会话详情响应"""
    id: str
    agent_id: str
    thread_id: str
    title: Optional[str]
    message_count: int
    messages: List[SessionMessage]
    created_at: datetime
    updated_at: datetime