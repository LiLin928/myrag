"""工作流模板模型"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean
from datetime import datetime
import uuid

from app.models.base import Base


class WorkflowTemplate(Base):
    """工作流模板表"""

    __tablename__ = "workflow_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 基本信息
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, index=True)  # RAG/dialog/data/approval/custom
    description = Column(Text, nullable=True)

    # 工作流定义
    definition = Column(JSON, nullable=False)  # nodes, edges
    default_input_variables = Column(JSON, nullable=True)  # 默认输入变量

    # 标签和属性
    tags = Column(JSON, nullable=True)  # ["推荐", "新手指引"]
    is_builtin = Column(Boolean, default=False)  # 是否内置模板
    usage_count = Column(Integer, default=0)  # 使用次数

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<WorkflowTemplate(id={self.id}, name={self.name}, category={self.category})>"