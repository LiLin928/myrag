"""工作流模板 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Dict, Any
import uuid

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.workflow.models.workflow_template import WorkflowTemplate
from app.workflow.models.workflow import Workflow, WorkflowStatus
from app.db import get_db

router = APIRouter(prefix="/workflow-templates", tags=["workflow-templates"])


@router.get("/")
async def list_templates(
    category: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取模板列表"""
    conditions = []
    if category:
        conditions.append(WorkflowTemplate.category == category)

    query = select(WorkflowTemplate).where(*conditions).order_by(
        WorkflowTemplate.is_builtin.desc(),  # 内置模板优先
        WorkflowTemplate.usage_count.desc(),
    )

    result = await db.execute(query)
    templates = result.scalars().all()

    return [
        {
            "id": str(t.id),
            "name": t.name,
            "category": t.category,
            "description": t.description,
            "tags": t.tags,
            "is_builtin": t.is_builtin,
            "usage_count": t.usage_count,
        }
        for t in templates
    ]


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取模板详情"""
    try:
        tid = uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template ID format")

    result = await db.execute(
        select(WorkflowTemplate).where(WorkflowTemplate.id == tid)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "id": str(template.id),
        "name": template.name,
        "category": template.category,
        "description": template.description,
        "definition": template.definition,
        "default_input_variables": template.default_input_variables,
        "tags": template.tags,
        "is_builtin": template.is_builtin,
        "usage_count": template.usage_count,
    }


@router.post("/")
async def create_template(
    name: str = Body(...),
    category: str = Body(...),
    description: str = Body(None),
    definition: Dict[str, Any] = Body(...),
    default_input_variables: Dict[str, Any] = Body(None),
    tags: List[str] = Body(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建自定义模板"""
    template = WorkflowTemplate(
        name=name,
        category=category,
        description=description,
        definition=definition,
        default_input_variables=default_input_variables,
        tags=tags or [],
        is_builtin=False,
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    return {"id": str(template.id), "name": template.name, "category": template.category}


@router.post("/{template_id}/create-workflow")
async def create_workflow_from_template(
    template_id: str,
    name: str = Body(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从模板创建工作流"""
    try:
        tid = uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template ID format")

    result = await db.execute(
        select(WorkflowTemplate).where(WorkflowTemplate.id == tid)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # 创建工作流
    workflow = Workflow(
        name=name or f"{template.name} - 副本",
        description=template.description,
        definition=template.definition,
        user_id=current_user.id,
        status=WorkflowStatus.DRAFT,
    )

    db.add(workflow)

    # 更新模板使用次数
    template.usage_count += 1

    await db.commit()
    await db.refresh(workflow)

    return {
        "id": str(workflow.id),
        "name": workflow.name,
        "template_name": template.name,
    }


@router.put("/{template_id}")
async def update_template(
    template_id: str,
    name: str = Body(None),
    description: str = Body(None),
    definition: Dict[str, Any] = Body(None),
    tags: List[str] = Body(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新模板"""
    try:
        tid = uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template ID format")

    result = await db.execute(
        select(WorkflowTemplate).where(
            and_(
                WorkflowTemplate.id == tid,
                WorkflowTemplate.is_builtin == False,  # 不能修改内置模板
            )
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found or is builtin")

    if name:
        template.name = name
    if description:
        template.description = description
    if definition:
        template.definition = definition
    if tags:
        template.tags = tags

    await db.commit()

    return {"id": str(template.id), "message": "Template updated"}


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除模板"""
    try:
        tid = uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template ID format")

    result = await db.execute(
        select(WorkflowTemplate).where(
            and_(
                WorkflowTemplate.id == tid,
                WorkflowTemplate.is_builtin == False,
            )
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found or is builtin")

    await db.delete(template)
    await db.commit()

    return {"message": "Template deleted"}