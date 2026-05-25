"""模型配置 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import enum

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.model_config import ModelConfig, ModelType
from app.services.model_service import ModelService
from app.db import get_db

router = APIRouter(prefix="/models", tags=["models"])


# 请求/响应模型
class ModelTypeEnum(str, enum.Enum):
    LLM = "llm"
    EMBEDDING = "embedding"
    RERANK = "rerank"


class ModelConfigCreate(BaseModel):
    """创建模型配置请求"""
    name: str = Field(..., min_length=1, max_length=100)
    type: ModelTypeEnum
    provider: str = Field(..., min_length=1, max_length=50)
    api_base: str = Field(..., min_length=1, max_length=255)
    api_key: str = Field(..., min_length=1)
    model_name: str = Field(..., min_length=1, max_length=100)
    context_length: Optional[int] = None
    max_tokens: Optional[int] = None
    temperature: Optional[int] = None  # 存储为整数(如 70 表示 0.7)
    dimension: Optional[int] = None
    batch_size: Optional[int] = None
    top_k: Optional[int] = None
    timeout: Optional[int] = 30
    extra_config: Optional[dict] = None


class ModelConfigUpdate(BaseModel):
    """更新模型配置请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    provider: Optional[str] = Field(None, min_length=1, max_length=50)
    api_base: Optional[str] = Field(None, min_length=1, max_length=255)
    api_key: Optional[str] = None
    model_name: Optional[str] = Field(None, min_length=1, max_length=100)
    context_length: Optional[int] = None
    max_tokens: Optional[int] = None
    temperature: Optional[int] = None
    dimension: Optional[int] = None
    batch_size: Optional[int] = None
    top_k: Optional[int] = None
    timeout: Optional[int] = None
    extra_config: Optional[dict] = None
    is_active: Optional[bool] = None


class ModelConfigResponse(BaseModel):
    """模型配置响应"""
    id: str
    name: str
    type: str
    provider: str
    api_base: str
    api_key: str  # 脱敏显示
    model_name: str
    context_length: Optional[int]
    max_tokens: Optional[int]
    temperature: Optional[int]
    dimension: Optional[int]
    batch_size: Optional[int]
    top_k: Optional[int]
    timeout: int
    extra_config: Optional[dict]
    is_active: bool
    is_default: bool
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelConfigListResponse(BaseModel):
    """模型配置列表响应"""
    items: List[ModelConfigResponse]
    total: int


class ToggleActiveRequest(BaseModel):
    """切换激活状态请求"""
    is_active: bool


class SetDefaultRequest(BaseModel):
    """设置默认模型请求"""
    model_id: str


@router.get("/", response_model=ModelConfigListResponse)
async def list_models(
    type: Optional[ModelTypeEnum] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取模型配置列表"""
    service = ModelService(db)
    model_type = ModelType(type.value) if type else None
    models, total = await service.list_models(model_type, is_active)

    return ModelConfigListResponse(
        items=[ModelConfigResponse(**service.mask_model_api_key(m)) for m in models],
        total=total,
    )


@router.post("/", response_model=ModelConfigResponse, status_code=201)
async def create_model(
    data: ModelConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建模型配置"""
    service = ModelService(db)
    model = await service.create_model(
        name=data.name,
        type=data.type.value,  # 传递字符串值
        provider=data.provider,
        api_base=data.api_base,
        api_key=data.api_key,
        model_name=data.model_name,
        created_by=str(current_user.id),
        context_length=data.context_length,
        max_tokens=data.max_tokens,
        temperature=data.temperature,
        dimension=data.dimension,
        batch_size=data.batch_size,
        top_k=data.top_k,
        timeout=data.timeout or 30,
        extra_config=data.extra_config,
    )

    return ModelConfigResponse(**service.mask_model_api_key(model))


@router.get("/default/{type}", response_model=ModelConfigResponse)
async def get_default_model(
    type: ModelTypeEnum,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取某类型的默认模型"""
    service = ModelService(db)
    model = await service.get_default_model(ModelType(type.value))

    if not model:
        raise HTTPException(status_code=404, detail=f"No default model for type {type.value}")

    return ModelConfigResponse(**service.mask_model_api_key(model))


@router.put("/default/{type}", response_model=ModelConfigResponse)
async def set_default_model(
    type: ModelTypeEnum,
    data: SetDefaultRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """设置某类型的默认模型"""
    service = ModelService(db)
    model = await service.set_default_model(data.model_id)

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    return ModelConfigResponse(**service.mask_model_api_key(model))


@router.get("/{model_id}", response_model=ModelConfigResponse)
async def get_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取模型配置详情"""
    service = ModelService(db)
    model = await service.get_model(model_id)

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    return ModelConfigResponse(**service.mask_model_api_key(model))


@router.put("/{model_id}", response_model=ModelConfigResponse)
async def update_model(
    model_id: str,
    data: ModelConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新模型配置"""
    service = ModelService(db)
    model = await service.get_model(model_id)

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # 权限检查: 创建者或管理员
    # TODO: 实际需检查 SYSTEM_ADMIN 权限
    # if str(model.created_by) != str(current_user.id):
    #     raise HTTPException(status_code=403, detail="No permission to update this model")

    updated = await service.update_model(
        model_id=model_id,
        **data.model_dump(exclude_none=True),
    )

    return ModelConfigResponse(**service.mask_model_api_key(updated))


@router.delete("/{model_id}")
async def delete_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除模型配置"""
    service = ModelService(db)
    model = await service.get_model(model_id)

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # TODO: 权限检查

    success = await service.delete_model(model_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete model")

    return {"deleted": model_id}


@router.put("/{model_id}/active", response_model=ModelConfigResponse)
async def toggle_model_active(
    model_id: str,
    data: ToggleActiveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """切换模型启用状态"""
    service = ModelService(db)
    model = await service.get_model(model_id)

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # 如果要设置的状态与当前状态不同,才进行更新
    if model.is_active != data.is_active:
        model = await service.toggle_active(model_id)

    return ModelConfigResponse(**service.mask_model_api_key(model))