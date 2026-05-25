"""Skill 数据模型"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

from app.models.base import Base


class SkillStatus(str, enum.Enum):
    """Skill 状态"""
    DRAFT = "draft"
    PUBLISHED = "published"
    DISABLED = "disabled"


class Skill(Base):
    """Skill 数据表"""

    __tablename__ = "skills"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 基本信息
    description = Column(Text, nullable=True)

    # 版本
    version = Column(String(20), default="1.0.0")
    previous_version_id = Column(String(36), ForeignKey("skills.id"), nullable=True)

    # 代码
    code = Column(Text, nullable=False)  # Python 代码（包含 execute 函数）
    internal_name = Column(String(64), nullable=False, unique=True, index=True)  # 固定标识符
    display_name = Column(String(128), nullable=True)  # 可编辑的显示名称

    # 权限与执行配置
    is_public = Column(Boolean, default=False, nullable=False, index=True)  # 是否公开
    entry_command = Column(String(256), nullable=True, server_default='python main.py')  # 入口命令
    working_directory = Column(String(512), nullable=True)  # 工作目录

    # Schema
    input_schema = Column(JSON, nullable=True)   # 输入参数 JSON Schema
    output_schema = Column(JSON, nullable=True)  # 输出参数 JSON Schema

    # 状态
    status = Column(Enum(SkillStatus), default=SkillStatus.DRAFT, index=True)
    enabled = Column(Boolean, default=True)

    # 元数据
    author = Column(String(64), nullable=True)
    tags = Column(JSON, nullable=True)
    skill_metadata = Column(JSON, nullable=True)

    # 生成信息
    generated_by_llm = Column(Boolean, default=False)
    generation_prompt = Column(Text, nullable=True)  # LLM 生成的原始提示

    # 统计
    execution_count = Column(Integer, default=0)
    last_executed_at = Column(DateTime, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    published_at = Column(DateTime, nullable=True)

    # 关系
    user = relationship("User")
    previous_version = relationship("Skill", remote_side=[id], foreign_keys=[previous_version_id])

    @property
    def name(self):
        """向后兼容：返回 internal_name"""
        return self.internal_name

    def __repr__(self):
        return f"<Skill(id={self.id}, internal_name={self.internal_name}, display_name={self.display_name})>"