"""系统提示词模板 API 路由"""

from typing import Optional, List
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.system_prompt_template import SystemPromptTemplate
from app.db import get_db

router = APIRouter(prefix="/system-prompts", tags=["system-prompts"])


# ============ Pydantic Schemas ============

class TemplateCreate(BaseModel):
    """创建模板请求"""
    name: str = Field(..., min_length=1, max_length=100, description="模板名称")
    description: Optional[str] = Field(None, max_length=500, description="模板描述")
    content: str = Field(..., min_length=1, description="模板内容")
    category: Optional[str] = Field(None, max_length=50, description="分类")
    is_public: bool = Field(False, description="是否公开")


class TemplateUpdate(BaseModel):
    """更新模板请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="模板名称")
    description: Optional[str] = Field(None, max_length=500, description="模板描述")
    content: Optional[str] = Field(None, min_length=1, description="模板内容")
    category: Optional[str] = Field(None, max_length=50, description="分类")
    is_public: Optional[bool] = Field(None, description="是否公开")


class TemplateResponse(BaseModel):
    """模板响应"""
    id: str
    user_id: str
    name: str
    description: Optional[str]
    content: str
    category: Optional[str]
    is_public: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CategoryCount(BaseModel):
    """分类统计"""
    category: Optional[str]
    count: int


# ============ Helper Functions ============

def validate_uuid(template_id: str) -> bool:
    """验证 UUID 格式"""
    try:
        UUID(template_id)
        return True
    except ValueError:
        return False


async def get_template_with_permission(
    db: AsyncSession,
    template_id: str,
    user_id: str,
) -> SystemPromptTemplate:
    """获取模板并检查权限"""
    if not validate_uuid(template_id):
        raise HTTPException(status_code=400, detail="无效的模板 ID 格式")

    result = await db.execute(
        select(SystemPromptTemplate).where(SystemPromptTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    # 检查权限：公开模板或所有者可以访问
    if not template.is_public and str(template.user_id) != user_id:
        raise HTTPException(status_code=403, detail="无权访问此模板")

    return template


def template_to_response(template: SystemPromptTemplate) -> TemplateResponse:
    """将模板模型转换为响应对象"""
    return template_to_response(template)


# ============ API Endpoints ============

@router.post("/", response_model=TemplateResponse)
async def create_template(
    data: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建系统提示词模板"""
    template = SystemPromptTemplate(
        user_id=str(current_user.id),
        name=data.name,
        description=data.description,
        content=data.content,
        category=data.category,
        is_public=data.is_public,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    return template_to_response(template)


@router.get("/", response_model=List[TemplateResponse])
async def list_templates(
    category: Optional[str] = Query(None, description="按分类筛选"),
    is_public: Optional[bool] = Query(None, description="按公开状态筛选"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出系统提示词模板

    显示公开模板 + 当前用户的私有模板
    排序：is_default DESC, created_at DESC
    """
    query = select(SystemPromptTemplate).where(
        or_(
            SystemPromptTemplate.is_public == True,
            SystemPromptTemplate.user_id == str(current_user.id),
        )
    )

    # 可选筛选条件
    if category is not None:
        query = query.where(SystemPromptTemplate.category == category)
    if is_public is not None:
        query = query.where(SystemPromptTemplate.is_public == is_public)

    # 排序：默认模板优先，然后按创建时间倒序
    query = query.order_by(
        SystemPromptTemplate.is_default.desc(),
        SystemPromptTemplate.created_at.desc(),
    )

    # 分页
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    templates = result.scalars().all()

    return [template_to_response(t) for t in templates]


@router.get("/categories", response_model=List[CategoryCount])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取分类列表及其模板数量

    返回格式: [{category, count}]
    """
    # 查询公开模板和当前用户的模板的分类统计
    query = (
        select(
            SystemPromptTemplate.category,
            func.count(SystemPromptTemplate.id).label("count"),
        )
        .where(
            or_(
                SystemPromptTemplate.is_public == True,
                SystemPromptTemplate.user_id == str(current_user.id),
            )
        )
        .group_by(SystemPromptTemplate.category)
        .order_by(func.count(SystemPromptTemplate.id).desc())
    )

    result = await db.execute(query)
    rows = result.all()

    return [CategoryCount(category=row.category, count=row.count) for row in rows]


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取模板详情

    验证 UUID 格式，检查权限（公开或所有者可访问）
    """
    template = await get_template_with_permission(
        db, template_id, str(current_user.id)
    )

    return template_to_response(template)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    data: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新模板

    不能更新默认模板
    只有所有者可以更新
    """
    template = await get_template_with_permission(
        db, template_id, str(current_user.id)
    )

    # 检查是否为默认模板
    if template.is_default:
        raise HTTPException(status_code=400, detail="无法更新默认模板")

    # 检查所有权
    if str(template.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="只有所有者可以更新模板")

    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)

    return template_to_response(template)


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除模板

    不能删除默认模板
    只有所有者可以删除
    """
    template = await get_template_with_permission(
        db, template_id, str(current_user.id)
    )

    # 检查是否为默认模板
    if template.is_default:
        raise HTTPException(status_code=400, detail="无法删除默认模板")

    # 检查所有权
    if str(template.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="只有所有者可以删除模板")

    await db.delete(template)
    await db.commit()

    return {"deleted": template_id}