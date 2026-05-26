"""工作流定义模型"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

from app.models.base import Base


class WorkflowStatus(str, enum.Enum):
    """工作流状态"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Workflow(Base):
    """工作流定义表"""

    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 基本信息
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(20), default="1.0.0")
    # 使用 String 类型存储状态值，而不是 PostgreSQL ENUM
    status = Column(String(20), default="draft", nullable=False, index=True)

    # 工作流定义（JSON）
    definition = Column(JSON, nullable=True)  # nodes, edges, variables

    # 元数据
    tags = Column(JSON, nullable=True)
    wf_metadata = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)

    # 关系
    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Workflow(id={self.id}, name={self.name}, status={self.status})>"


# 工作流节点定义 Schema（JSON）
WORKFLOW_NODE_SCHEMA = {
    "id": "string",           # 节点唯一 ID
    "type": "string",         # 节点类型（start/end/llm/rag/code 等）
    "position": {"x": 0, "y": 0},
    "data": {
        "config": {},          # 节点配置
        "inputs": [],          # 输入端口
        "outputs": [],         # 输出端口
    }
}

# 工作流边定义 Schema
WORKFLOW_EDGE_SCHEMA = {
    "id": "string",
    "source": "string",       # 源节点 ID
    "target": "string",       # 目标节点 ID
    "sourceHandle": "string", # 源端口
    "targetHandle": "string", # 目标端口
    "label": "string",        # 边标签（条件）
}