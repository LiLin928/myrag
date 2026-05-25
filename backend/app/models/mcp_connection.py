"""MCP Connection 数据模型"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, Boolean, Enum
from datetime import datetime
import enum
import uuid

from app.models.base import Base


class TransportType(str, enum.Enum):
    """传输类型"""
    STDIO = "stdio"
    SSE = "sse"
    WEBSOCKET = "websocket"


class SyncStatus(str, enum.Enum):
    """同步状态"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class McpConnection(Base):
    """MCP Server 连接配置"""

    __tablename__ = "mcp_connections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    # 基本信息
    name = Column(String(64), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # 连接配置
    transport_type = Column(Enum(TransportType), default=TransportType.SSE, nullable=False)
    connection_url = Column(String(512), nullable=True)
    command = Column(String(256), nullable=True)
    args = Column(JSON, nullable=True)
    env_vars = Column(JSON, nullable=True)

    # 状态
    is_enabled = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    sync_status = Column(Enum(SyncStatus), default=SyncStatus.PENDING, nullable=False)
    sync_error = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<McpConnection(id={self.id}, name={self.name}, transport={self.transport_type})>"