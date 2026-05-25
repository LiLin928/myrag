"""SkillFile 数据模型 - 技能文件管理"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import Base


class SkillFile(Base):
    """技能文件数据表"""

    __tablename__ = "skill_files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    skill_id = Column(String(36), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)

    # 文件信息
    file_path = Column(String(255), nullable=False)  # 相对路径，如 main.py, scripts/preprocess.sh
    file_type = Column(String(32), nullable=True)    # python, shell, markdown, yaml, json
    file_size = Column(Integer, default=0)          # 文件大小（字节）
    content_hash = Column(String(64), nullable=True) # SHA256 哈希

    # 标记
    is_entry = Column(Boolean, default=False, nullable=False)  # 是否为入口文件

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    skill = relationship("Skill", backref="files")

    # 唯一约束：同一技能内文件路径唯一
    __table_args__ = (
        Index('ix_skill_files_skill_path', 'skill_id', 'file_path', unique=True),
    )

    def __repr__(self):
        return f"<SkillFile(skill_id={self.skill_id}, path={self.file_path}, type={self.file_type})>"