"""Skills API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File
from typing import Dict, Any, List as TypingList
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import uuid
import re

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.skill import Skill, SkillStatus
from app.models.skill_file import SkillFile
from app.services.skill_service import skill_service
from app.services.skill_file_service import skill_file_service
from app.workflow.sandbox.code_executor import get_code_executor
from app.db import get_db
from app.utils.file_storage import file_storage

router = APIRouter(prefix="/skills", tags=["skills"])


@router.post("/")
async def create_skill(
    internal_name: str = Body(...),
    display_name: str = Body(None),
    description: str = Body(None),
    code: str = Body(default=""),
    input_schema: Dict[str, str] = Body(default={}),
    output_schema: Dict[str, str] = Body(default={}),
    is_public: bool = Body(default=False),
    entry_command: str = Body(default="python main.py"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建 Skill"""
    # 验证 internal_name 格式
    if not re.match(r'^[a-z][a-z0-9_]*$', internal_name):
        raise HTTPException(
            status_code=400,
            detail="internal_name must start with lowercase letter and contain only lowercase letters, numbers, and underscores"
        )

    try:
        skill = await skill_service.create_skill(
            db=db,
            internal_name=internal_name,
            code=code,
            description=description or "",
            user_id=str(current_user.id),
            input_schema=input_schema,
            output_schema=output_schema,
            display_name=display_name,
            is_public=is_public,
            entry_command=entry_command,
        )

        return {
            "id": str(skill.id),
            "internal_name": skill.internal_name,
            "display_name": skill.display_name,
            "description": skill.description,
            "version": skill.version,
            "status": skill.status,
            "is_public": skill.is_public,
            "entry_command": skill.entry_command,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generate")
async def generate_skill(
    requirement: str = Body(...),
    skill_name: str = Body(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """LLM 自动生成 Skill"""
    try:
        skill = await skill_service.generate_skill_with_llm(
            db=db,
            requirements=requirement,
            user_id=str(current_user.id),
            skill_name=skill_name,
        )

        return {
            "id": str(skill.id),
            "name": skill.name,
            "description": skill.description,
            "code": skill.code,
            "version": skill.version,
            "generated_by_llm": skill.generated_by_llm,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def list_skills(
    status: SkillStatus = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出所有 Skills"""
    skills = await skill_service.list_skills(
        db=db,
        user_id=str(current_user.id),
        status=status,
    )

    return [
        {
            "id": str(s.id),
            "internal_name": s.internal_name,
            "display_name": s.display_name,
            "description": s.description,
            "version": s.version,
            "status": s.status,
            "is_public": s.is_public,
            "execution_count": s.execution_count,
        }
        for s in skills
    ]


@router.get("/{skill_id}")
async def get_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取 Skill 详情"""
    skill_uuid = uuid.UUID(skill_id)
    result = await db.execute(select(Skill).where(Skill.id == skill_uuid))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # 获取关联的文件列表
    files = await skill_file_service.list_files(db, skill_id)

    return {
        "id": str(skill.id),
        "internal_name": skill.internal_name,
        "display_name": skill.display_name,
        "description": skill.description,
        "code": skill.code,
        "input_schema": skill.input_schema,
        "output_schema": skill.output_schema,
        "version": skill.version,
        "status": skill.status,
        "is_public": skill.is_public,
        "entry_command": skill.entry_command,
        "working_directory": skill.working_directory,
        "generated_by_llm": skill.generated_by_llm,
        "files": [
            {
                "id": str(f.id),
                "file_path": f.file_path,
                "file_type": f.file_type,
                "file_size": f.file_size,
                "is_entry": f.is_entry,
            }
            for f in files
        ],
    }


@router.post("/{skill_name}/execute")
async def execute_skill(
    skill_name: str,
    input_data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """执行 Skill"""
    try:
        result = await skill_service.execute_skill(
            db=db,
            skill_name=skill_name,
            input_data=input_data,
        )

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error"))

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{skill_id}/version")
async def create_new_version(
    skill_id: str,
    new_code: str = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建新版本"""
    try:
        new_skill = await skill_service.create_new_version(
            db=db,
            skill_id=skill_id,
            new_code=new_code,
            user_id=str(current_user.id),
        )

        return {
            "id": str(new_skill.id),
            "name": new_skill.name,
            "version": new_skill.version,
            "previous_version_id": str(new_skill.previous_version_id),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{skill_id}")
async def delete_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除 Skill"""
    skill_uuid = uuid.UUID(skill_id)
    result = await db.execute(select(Skill).where(Skill.id == skill_uuid))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # 删除关联文件
    await db.execute(delete(SkillFile).where(SkillFile.skill_id == skill_uuid))

    # 删除技能记录
    await db.execute(delete(Skill).where(Skill.id == skill_uuid))
    await db.commit()

    # 删除文件系统目录
    await file_storage.delete_skill_directory(skill.internal_name)

    return {"deleted": skill_id}


@router.patch("/{skill_id}")
async def update_skill(
    skill_id: str,
    description: str = Body(None),
    code: str = Body(None),
    enabled: bool = Body(None),
    status: SkillStatus = Body(None),
    display_name: str = Body(None),
    is_public: bool = Body(None),
    entry_command: str = Body(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新 Skill"""
    skill_uuid = uuid.UUID(skill_id)
    result = await db.execute(select(Skill).where(Skill.id == skill_uuid))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    if description is not None:
        skill.description = description

    if code is not None:
        code_executor = get_code_executor()
        validation = await code_executor.validate_code(code)
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail=f"Invalid code: {validation['error']}")
        skill.code = code

    if enabled is not None:
        skill.enabled = enabled

    if status is not None:
        skill.status = status

    if display_name is not None:
        skill.display_name = display_name

    if is_public is not None:
        skill.is_public = is_public

    if entry_command is not None:
        skill.entry_command = entry_command

    await db.commit()
    await db.refresh(skill)

    return {
        "id": str(skill.id),
        "internal_name": skill.internal_name,
        "display_name": skill.display_name,
        "description": skill.description,
        "version": skill.version,
        "status": skill.status,
        "is_public": skill.is_public,
        "entry_command": skill.entry_command,
        "enabled": skill.enabled,
    }


# ==================== File Management Endpoints ====================

@router.get("/{skill_id}/files")
async def list_skill_files(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出技能的所有文件"""
    skill_uuid = uuid.UUID(skill_id)
    result = await db.execute(select(Skill).where(Skill.id == skill_uuid))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    files = await skill_file_service.list_files(db, skill_id)

    return [
        {
            "id": str(f.id),
            "file_path": f.file_path,
            "file_type": f.file_type,
            "file_size": f.file_size,
            "content_hash": f.content_hash,
            "is_entry": f.is_entry,
            "created_at": f.created_at.isoformat(),
            "updated_at": f.updated_at.isoformat(),
        }
        for f in files
    ]


@router.post("/{skill_id}/files")
async def create_skill_file(
    skill_id: str,
    file_path: str = Body(...),
    content: str = Body(...),
    is_entry: bool = Body(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建技能文件"""
    try:
        skill_file = await skill_file_service.create_file(
            db=db,
            skill_id=skill_id,
            file_path=file_path,
            content=content,
            is_entry=is_entry,
            user_id=str(current_user.id),
        )

        return {
            "id": str(skill_file.id),
            "skill_id": str(skill_file.skill_id),
            "file_path": skill_file.file_path,
            "file_type": skill_file.file_type,
            "file_size": skill_file.file_size,
            "is_entry": skill_file.is_entry,
            "created_at": skill_file.created_at.isoformat(),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{skill_id}/files/{file_path:path}")
async def get_skill_file(
    skill_id: str,
    file_path: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取技能文件内容"""
    try:
        file_data = await skill_file_service.get_file(
            db=db,
            skill_id=skill_id,
            file_path=file_path,
        )

        return file_data

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{skill_id}/files/{file_path:path}")
async def update_skill_file(
    skill_id: str,
    file_path: str,
    content: str = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新技能文件"""
    try:
        skill_file = await skill_file_service.update_file(
            db=db,
            skill_id=skill_id,
            file_path=file_path,
            content=content,
            user_id=str(current_user.id),
        )

        return {
            "id": str(skill_file.id),
            "skill_id": str(skill_file.skill_id),
            "file_path": skill_file.file_path,
            "file_size": skill_file.file_size,
            "updated_at": skill_file.updated_at.isoformat(),
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{skill_id}/files/{file_path:path}")
async def delete_skill_file(
    skill_id: str,
    file_path: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除技能文件"""
    try:
        await skill_file_service.delete_file(
            db=db,
            skill_id=skill_id,
            file_path=file_path,
            user_id=str(current_user.id),
        )

        return {"deleted": file_path}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{skill_id}/files/upload")
async def upload_skill_files(
    skill_id: str,
    files: TypingList[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量上传技能文件"""
    skill_uuid = uuid.UUID(skill_id)
    result = await db.execute(select(Skill).where(Skill.id == skill_uuid))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    uploaded_files = []

    for upload_file in files:
        # 读取文件内容
        content = await upload_file.read()

        # 尝试解码为文本，如果失败则使用二进制
        try:
            content_str = content.decode('utf-8')
        except UnicodeDecodeError:
            content_str = content

        try:
            skill_file = await skill_file_service.create_file(
                db=db,
                skill_id=skill_id,
                file_path=upload_file.filename,
                content=content_str,
                is_entry=False,
                user_id=str(current_user.id),
            )

            uploaded_files.append({
                "id": str(skill_file.id),
                "file_path": skill_file.file_path,
                "file_size": skill_file.file_size,
            })

        except ValueError as e:
            # 文件已存在，跳过或记录错误
            uploaded_files.append({
                "file_path": upload_file.filename,
                "error": str(e),
            })

    return {"uploaded": uploaded_files}