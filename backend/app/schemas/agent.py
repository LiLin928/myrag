"""Agent Pydantic Schema"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class KnowledgeBindingBase(BaseModel):
    """知识库绑定基础 Schema"""
    knowledge_base_id: str
    search_type: str = Field(default="hybrid")
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    priority: int = Field(default=0, ge=0)


class KnowledgeBindingCreate(KnowledgeBindingBase):
    """创建知识库绑定"""
    pass


class KnowledgeBindingResponse(KnowledgeBindingBase):
    """知识库绑定响应"""
    id: str
    agent_id: str
    knowledge_base_name: Optional[str] = None
    created_at: datetime


class AgentBase(BaseModel):
    """Agent 基础 Schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    model_id: str
    system_prompt: Optional[str] = None
    use_knowledge: bool = False
    use_tools: bool = False
    use_skills: bool = False


class AgentCreate(AgentBase):
    """创建 Agent Schema"""
    knowledge_bindings: List[KnowledgeBindingCreate] = []
    tool_bindings: List[str] = []
    skill_bindings: List[str] = []


class AgentUpdate(BaseModel):
    """更新 Agent Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    model_id: Optional[str] = None
    system_prompt: Optional[str] = None
    use_knowledge: Optional[bool] = None
    use_tools: Optional[bool] = None
    use_skills: Optional[bool] = None
    search_type: Optional[str] = None
    top_k: Optional[int] = Field(None, ge=1, le=20)
    score_threshold: Optional[int] = Field(None, ge=0, le=100)
    knowledge_bindings: Optional[List[KnowledgeBindingCreate]] = None
    tool_bindings: Optional[List[str]] = None
    skill_bindings: Optional[List[str]] = None


class AgentResponse(AgentBase):
    """Agent 响应 Schema"""
    id: str
    user_id: str
    search_type: str
    top_k: int
    score_threshold: int
    created_at: datetime
    updated_at: datetime

    model_name: Optional[str] = None
    knowledge_bindings: List[KnowledgeBindingResponse] = []
    tool_bindings: List[str] = []
    skill_bindings: List[str] = []


class AgentListResponse(BaseModel):
    """Agent 列表响应"""
    id: str
    name: str
    description: Optional[str]
    model_name: Optional[str]
    use_knowledge: bool
    use_tools: bool
    use_skills: bool
    created_at: datetime
    updated_at: datetime