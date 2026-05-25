"""Tool 数据模型"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

from app.models.base import Base


class ToolType(str, enum.Enum):
    """工具类型"""
    HTTP = "http"
    MCP = "mcp"


class Tool(Base):
    """工具数据表"""

    __tablename__ = "tools"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    # 基本信息
    name = Column(String(64), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # 工具类型
    tool_type = Column(Enum(ToolType), default=ToolType.HTTP, nullable=False)

    # 工具配置（JSON）
    config = Column(JSON, nullable=False, default=dict)

    # 输入输出 Schema
    input_schema = Column(JSON, nullable=True)
    output_schema = Column(JSON, nullable=True)

    # 权限与状态
    is_public = Column(Boolean, default=False, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)

    # MCP 关联字段（预留）
    mcp_connection_id = Column(String(36), ForeignKey("mcp_connections.id"), nullable=True)
    mcp_tool_name = Column(String(128), nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    owner = relationship("User", foreign_keys=[owner_id])
    mcp_connection = relationship("McpConnection", foreign_keys=[mcp_connection_id])

    def __repr__(self):
        return f"<Tool(id={self.id}, name={self.name}, type={self.tool_type})>"