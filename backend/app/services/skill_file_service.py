"""SkillFile 业务服务

管理技能文件的 CRUD、版本快照创建
"""

from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime
import uuid
import logging

from app.models.skill import Skill
from app.models.skill_file import SkillFile
from app.models.skill_version import SkillVersion
from app.utils.file_storage import file_storage

logger = logging.getLogger(__name__)


class SkillFileService:
    """技能文件服务"""

    async def create_file(
        self,
        db: AsyncSession,
        skill_id: str,
        file_path: str,
        content: str,
        is_entry: bool = False,
        user_id: Optional[str] = None,
    ) -> SkillFile:
        """创建文件

        Args:
            db: 数据库会话
            skill_id: 技能 ID
            file_path: 文件相对路径
            content: 文件内容
            is_entry: 是否为入口文件
            user_id: 创建者 ID

        Returns:
            SkillFile 实例
        """
        try:
            # 获取技能
            skill_uuid = uuid.UUID(skill_id)
            result = await db.execute(select(Skill).where(Skill.id == skill_uuid))
            skill = result.scalar_one_or_none()

            if not skill:
                raise ValueError(f"Skill '{skill_id}' not found")

            # 检查文件是否已存在
            existing = await db.execute(
                select(SkillFile).where(
                    SkillFile.skill_id == skill_uuid,
                    SkillFile.file_path == file_path,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"File '{file_path}' already exists in this skill")

            # 写入文件系统
            file_info = await file_storage.create_file(
                skill.internal_name,
                file_path,
                content,
            )

            # 创建数据库记录
            skill_file = SkillFile(
                skill_id=skill_uuid,
                file_path=file_path,
                file_type=file_storage.get_file_type(file_path),
                file_size=file_info["size"],
                content_hash=file_info["hash"],
                is_entry=is_entry,
            )

            db.add(skill_file)

            # 更新技能的 working_directory
            skill.working_directory = str(file_storage.get_skill_directory(skill.internal_name))

            # 创建版本快照
            await self._create_version_snapshot(db, skill, user_id, f"新增文件: {file_path}")

            await db.commit()
            await db.refresh(skill_file)

            return skill_file
        except Exception:
            await db.rollback()
            raise

    async def get_file(
        self,
        db: AsyncSession,
        skill_id: str,
        file_path: str,
    ) -> Dict:
        """获取文件内容和元数据"""
        skill_uuid = uuid.UUID(skill_id)
        result = await db.execute(select(Skill).where(Skill.id == skill_uuid))
        skill = result.scalar_one_or_none()

        if not skill:
            raise ValueError(f"Skill '{skill_id}' not found")

        # 从数据库获取元数据
        file_result = await db.execute(
            select(SkillFile).where(
                SkillFile.skill_id == skill_uuid,
                SkillFile.file_path == file_path,
            )
        )
        skill_file = file_result.scalar_one_or_none()

        if not skill_file:
            raise ValueError(f"File '{file_path}' not found")

        # 从文件系统读取内容
        content = await file_storage.read_file(skill.internal_name, file_path)

        return {
            "id": str(skill_file.id),
            "file_path": skill_file.file_path,
            "file_type": skill_file.file_type,
            "file_size": skill_file.file_size,
            "content_hash": skill_file.content_hash,
            "is_entry": skill_file.is_entry,
            "content": content,
            "created_at": skill_file.created_at.isoformat(),
            "updated_at": skill_file.updated_at.isoformat(),
        }

    async def update_file(
        self,
        db: AsyncSession,
        skill_id: str,
        file_path: str,
        content: str,
        user_id: Optional[str] = None,
    ) -> SkillFile:
        """更新文件内容"""
        try:
            skill_uuid = uuid.UUID(skill_id)
            result = await db.execute(select(Skill).where(Skill.id == skill_uuid))
            skill = result.scalar_one_or_none()

            if not skill:
                raise ValueError(f"Skill '{skill_id}' not found")

            # 获取文件记录
            file_result = await db.execute(
                select(SkillFile).where(
                    SkillFile.skill_id == skill_uuid,
                    SkillFile.file_path == file_path,
                )
            )
            skill_file = file_result.scalar_one_or_none()

            if not skill_file:
                raise ValueError(f"File '{file_path}' not found")

            # 更新文件系统
            file_info = await file_storage.update_file(
                skill.internal_name,
                file_path,
                content,
            )

            # 更新数据库记录
            skill_file.file_size = file_info["size"]
            skill_file.content_hash = file_info["hash"]
            skill_file.updated_at = datetime.utcnow()

            # 创建版本快照
            await self._create_version_snapshot(db, skill, user_id, f"修改文件: {file_path}")

            await db.commit()
            await db.refresh(skill_file)

            return skill_file
        except Exception:
            await db.rollback()
            raise

    async def delete_file(
        self,
        db: AsyncSession,
        skill_id: str,
        file_path: str,
        user_id: Optional[str] = None,
    ):
        """删除文件"""
        try:
            skill_uuid = uuid.UUID(skill_id)
            result = await db.execute(select(Skill).where(Skill.id == skill_uuid))
            skill = result.scalar_one_or_none()

            if not skill:
                raise ValueError(f"Skill '{skill_id}' not found")

            # 获取文件记录
            file_result = await db.execute(
                select(SkillFile).where(
                    SkillFile.skill_id == skill_uuid,
                    SkillFile.file_path == file_path,
                )
            )
            skill_file = file_result.scalar_one_or_none()

            if not skill_file:
                raise ValueError(f"File '{file_path}' not found")

            # 删除文件系统文件
            await file_storage.delete_file(skill.internal_name, file_path)

            # 删除数据库记录
            await db.delete(skill_file)

            # 创建版本快照
            await self._create_version_snapshot(db, skill, user_id, f"删除文件: {file_path}")

            await db.commit()
        except Exception:
            await db.rollback()
            raise

    async def list_files(
        self,
        db: AsyncSession,
        skill_id: str,
    ) -> List[SkillFile]:
        """列出技能所有文件"""
        skill_uuid = uuid.UUID(skill_id)
        result = await db.execute(
            select(SkillFile).where(SkillFile.skill_id == skill_uuid).order_by(SkillFile.file_path)
        )
        return result.scalars().all()

    async def upload_files(
        self,
        db: AsyncSession,
        skill_id: str,
        files: List[Dict],  # [{path, content}]
        user_id: Optional[str] = None,
    ) -> List[SkillFile]:
        """批量上传文件

        不使用 create_file（会单独提交事务），而是内联逻辑，最后统一提交。
        """
        try:
            created_files = []

            # 获取技能
            skill_uuid = uuid.UUID(skill_id)
            result = await db.execute(select(Skill).where(Skill.id == skill_uuid))
            skill = result.scalar_one_or_none()

            if not skill:
                raise ValueError(f"Skill '{skill_id}' not found")

            # 更新技能的 working_directory
            skill.working_directory = str(file_storage.get_skill_directory(skill.internal_name))

            # 1. 先将所有文件写入文件系统
            for file_data in files:
                file_path = file_data["path"]
                content = file_data["content"]

                # 检查文件是否已存在
                existing = await db.execute(
                    select(SkillFile).where(
                        SkillFile.skill_id == skill_uuid,
                        SkillFile.file_path == file_path,
                    )
                )
                if existing.scalar_one_or_none():
                    raise ValueError(f"File '{file_path}' already exists in this skill")

                # 写入文件系统
                file_info = await file_storage.create_file(
                    skill.internal_name,
                    file_path,
                    content,
                )

                # 创建数据库记录（不提交）
                skill_file = SkillFile(
                    skill_id=skill_uuid,
                    file_path=file_path,
                    file_type=file_storage.get_file_type(file_path),
                    file_size=file_info["size"],
                    content_hash=file_info["hash"],
                    is_entry=file_data.get("is_entry", False),
                )

                db.add(skill_file)
                created_files.append(skill_file)

            # 2. 创建一个版本快照
            file_names = [f["path"] for f in files]
            await self._create_version_snapshot(
                db, skill, user_id,
                f"批量上传文件: {', '.join(file_names)}"
            )

            # 3. 统一提交
            await db.commit()

            # 刷新所有文件记录
            for skill_file in created_files:
                await db.refresh(skill_file)

            return created_files
        except Exception:
            await db.rollback()
            raise

    async def _create_version_snapshot(
        self,
        db: AsyncSession,
        skill: Skill,
        user_id: Optional[str] = None,
        change_summary: Optional[str] = None,
    ):
        """创建版本快照"""
        # 获取当前最新版本号
        result = await db.execute(
            select(SkillVersion)
            .where(SkillVersion.skill_id == skill.id)
            .order_by(SkillVersion.version_number.desc())
            .limit(1)
        )
        latest_version = result.scalar_one_or_none()

        next_version_number = (latest_version.version_number + 1) if latest_version else 1

        # 获取当前所有文件
        files_result = await db.execute(
            select(SkillFile).where(SkillFile.skill_id == skill.id)
        )
        files = files_result.scalars().all()

        # 构建 manifest
        manifest = [
            {"path": f.file_path, "hash": f.content_hash, "size": f.file_size}
            for f in files
        ]

        # 创建版本记录
        version = SkillVersion(
            skill_id=skill.id,
            version_number=next_version_number,
            files_manifest=manifest,
            change_summary=change_summary,
            created_by=uuid.UUID(user_id) if user_id else None,
        )

        db.add(version)


# 全局服务实例
skill_file_service = SkillFileService()