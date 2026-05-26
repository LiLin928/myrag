"""工作流执行日志模型

记录工作流执行过程中每个节点的详细日志
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

from app.models.base import Base


class LogEventType(str, enum.Enum):
    """日志事件类型"""
    START = "start"
    PROGRESS = "progress"
    COMPLETE = "complete"
    ERROR = "error"


class WorkflowExecutionLog(Base):
    """工作流执行日志表"""

    __tablename__ = "workflow_execution_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id = Column(String(36), ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False, index=True)

    # 节点信息
    node_id = Column(String(64), nullable=False, index=True)
    node_name = Column(String(128), nullable=True)
    node_type = Column(String(32), nullable=True)

    # 事件信息
    event_type = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 执行数据
    input_data = Column(JSON, nullable=True)    # 节点输入（可选脱敏）
    output_data = Column(JSON, nullable=True)   # 节点输出
    error_message = Column(Text, nullable=True) # 错误信息
    duration_ms = Column(Integer, nullable=True) # 执行耗时（毫秒）

    # 进度信息（用于长时间节点）
    progress_percent = Column(Integer, nullable=True)
    progress_message = Column(Text, nullable=True)

    # 关系
    execution = relationship("WorkflowExecution", back_populates="logs")

    def __repr__(self):
        return f"<WorkflowExecutionLog(id={self.id}, node={self.node_id}, event={self.event_type})>"