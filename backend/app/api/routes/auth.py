"""认证 API"""
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.dependencies import get_db
from app.config import get_settings
from app.models.user import User
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.api.dependencies.auth import get_current_user, get_redis

router = APIRouter(prefix="/auth", tags=["认证"])
settings = get_settings()


# 请求/响应模型
class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)


class UserLoginRequest(BaseModel):
    """用户登录请求"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfoResponse(BaseModel):
    """用户信息响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    is_superuser: bool


class PasswordChangeRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    """用户注册"""
    user_service = UserService(db)
    auth_service = AuthService(redis_client)

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

    # 创建令牌
    tokens = await auth_service.create_tokens(str(user.id))
    return TokenResponse(**tokens)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    """用户登录"""
    user_service = UserService(db)
    auth_service = AuthService(redis_client)

    # 验证用户
    user = await user_service.authenticate(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被停用",
        )

    # 创建令牌
    tokens = await auth_service.create_tokens(str(user.id))
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    redis_client: redis.Redis = Depends(get_redis),
):
    """刷新令牌"""
    auth_service = AuthService(redis_client)

    tokens = await auth_service.refresh_access_token(request.refresh_token)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(**tokens)


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis),
):
    """登出"""
    # 注意：实际使用时需要从前端传递 refresh_token
    # 这里简化处理，只返回成功
    return {"message": "登出成功"}


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """获取当前用户信息"""
    return UserInfoResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
    )


@router.put("/me/password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码"""
    user_service = UserService(db)

    success = await user_service.change_password(
        str(current_user.id),
        request.old_password,
        request.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误",
        )

    return {"message": "密码修改成功"}
