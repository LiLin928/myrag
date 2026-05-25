"""SkillVersion 数据模型 - 版本快照管理"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import Base


class SkillVersion(Base):
    """技能版本快照数据表"""

    __tablename__ = "skill_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    skill_id = Column(String(36), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)

    # 版本信息
    version_number = Column(Integer, nullable=False)  # 自增版本号 (1, 2, 3...)
    files_manifest = Column(JSON, nullable=False, default=list)  # [{path, hash, size}]
    change_summary = Column(Text, nullable=True)  # 变更摘要

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    # 关系
    skill = relationship("Skill", backref="versions")
    creator = relationship("User", foreign_keys=[created_by])

    # 唯一约束：同一技能内版本号唯一
    __table_args__ = (
        Index('ix_skill_versions_skill_number', 'skill_id', 'version_number', unique=True),
    )

    def __repr__(self):
        return f"<SkillVersion(skill_id={self.skill_id}, version={self.version_number})>"