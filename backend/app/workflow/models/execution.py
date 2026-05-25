"""工作流执行记录模型"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

from app.models.base import Base


class ExecutionStatus(str, enum.Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"       # 人工介入暂停
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowExecution(Base):
    """工作流执行记录表"""

    __tablename__ = "workflow_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 执行状态
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING, index=True)
    thread_id = Column(String(64), nullable=False, unique=True)  # LangGraph thread ID

    # 执行追踪
    current_node = Column(String(64), nullable=True)
    node_outputs = Column(JSON, nullable=True)  # 各节点输出
    variables = Column(JSON, nullable=True)     # 工作流变量

    # 人工介入
    human_prompt = Column(Text, nullable=True)
    human_input = Column(Text, nullable=True)

    # 错误信息
    error_message = Column(Text, nullable=True)
    error_node = Column(String(64), nullable=True)

    # 时间戳
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    workflow = relationship("Workflow", back_populates="executions")
    logs = relationship("WorkflowExecutionLog", back_populates="execution", order_by="WorkflowExecutionLog.timestamp")

    def __repr__(self):
        return f"<WorkflowExecution(id={self.id}, status={self.status}, thread_id={self.thread_id})>"