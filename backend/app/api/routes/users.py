"""用户管理 API"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.user import User
from app.services.user_service import UserService
from app.services.user_model_service import user_model_service
from app.api.dependencies.auth import get_current_user, get_current_superuser

router = APIRouter(prefix="/users", tags=["用户管理"])


class UserCreateRequest(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)


class UserUpdateRequest(BaseModel):
    """更新用户请求"""
    full_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)


class UserResponse(BaseModel):
    """用户响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    is_superuser: bool


class UserListResponse(BaseModel):
    """用户列表响应"""
    items: List[UserResponse]
    total: int


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """获取用户列表"""
    user_service = UserService(db)
    users, total = await user_service.list_users(skip, limit)

    return UserListResponse(
        items=[
            UserResponse(
                id=str(user.id),
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                avatar_url=user.avatar_url,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
            )
            for user in users
        ],
        total=total,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """创建用户"""
    user_service = UserService(db)

    # 检查用户名是否已存在
    existing = await user_service.get_by_username(request.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    # 检查邮箱是否已存在
    existing = await user_service.get_by_email(request.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册",
        )

    # 创建用户
    user = await user_service.create_user(
        username=request.username,
        email=request.email,
        password=request.password,
        full_name=request.full_name,
    )

    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """获取用户详情"""
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """更新用户"""
    user_service = UserService(db)
    user = await user_service.update_user(
        user_id=user_id,
        full_name=request.full_name,
        avatar_url=request.avatar_url,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
    )


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """激活用户"""
    user_service = UserService(db)
    success = await user_service.activate_user(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    return {"message": "用户已激活"}


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """停用用户"""
    user_service = UserService(db)
    success = await user_service.deactivate_user(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    return {"message": "用户已停用"}


# ============= 用户模型配置 API =============


class BindModelRequest(BaseModel):
    """绑定模型请求"""
    is_default: bool = False


class ModelConfigBrief(BaseModel):
    """模型配置简要信息"""
    id: str
    name: str
    type: str
    provider: str
    model_name: str
    is_default: bool = False


class UserModelsResponse(BaseModel):
    """用户模型列表响应"""
    models: List[ModelConfigBrief]


@router.get("/me/models", response_model=UserModelsResponse)
async def get_my_models(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户绑定的模型列表"""
    # 获取用户绑定的所有模型
    models = await user_model_service.get_user_models(db, str(current_user.id))

    # 获取每个模型的默认状态
    model_briefs = []
    for model in models:
        # 检查是否是用户的默认模型
        default_model = await user_model_service.get_user_default_model(
            db, str(current_user.id), model.type
        )
        is_default = default_model and str(default_model.id) == str(model.id)

        model_briefs.append(
            ModelConfigBrief(
                id=str(model.id),
                name=model.name,
                type=model.type,
                provider=model.provider,
                model_name=model.model_name,
                is_default=is_default,
            )
        )

    return UserModelsResponse(models=model_briefs)


@router.post("/me/models/{model_id}/bind")
async def bind_model(
    model_id: str,
    request: BindModelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """绑定模型到当前用户"""
    try:
        await user_model_service.bind_model_to_user(
            db=db,
            user_id=str(current_user.id),
            model_config_id=model_id,
            is_default=request.is_default,
        )
        return {"message": "模型绑定成功"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/me/models/{model_id}/set-default")
async def set_default_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """设置默认模型"""
    try:
        await user_model_service.set_user_default_model(
            db=db,
            user_id=str(current_user.id),
            model_config_id=model_id,
        )
        return {"message": "默认模型设置成功"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/me/models/{model_id}")
async def unbind_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """解绑模型"""
    await user_model_service.unbind_model(
        db=db,
        user_id=str(current_user.id),
        model_config_id=model_id,
    )
    return {"message": "模型解绑成功"}