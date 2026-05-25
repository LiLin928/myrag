"""认证依赖"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.user import User
from app.services.user_service import UserService
from app.core.security import decode_token
import redis.asyncio as redis
from app.config import get_settings

settings = get_settings()

# HTTP Bearer 认证方案
security = HTTPBearer(auto_error=False)


async def get_redis() -> redis.Redis:
    """获取 Redis 客户端"""
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    token = credentials.credentials

    # 解码令牌
    payload = decode_token(token)
    if not payload:
        raise credentials_exception

    user_id = payload.get("sub")
    token_type = payload.get("type")

    if not user_id or token_type != "access":
        raise credentials_exception

    # 检查令牌是否在黑名单中
    import hashlib

    token_key = f"token:blacklist:{hashlib.sha256(token.encode()).hexdigest()}"
    if await redis_client.get(token_key):
        raise credentials_exception

    # 获取用户
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)

    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="用户已被停用"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="用户已被停用"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前超级管理员"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="需要超级管理员权限"
        )
    return current_user


class OptionalAuth:
    """可选认证 - 不强制要求登录"""

    def __init__(self):
        self.security = HTTPBearer(auto_error=False)

    async def __call__(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: AsyncSession = Depends(get_db),
    ) -> Optional[User]:
        if not credentials:
            return None

        token = credentials.credentials
        payload = decode_token(token)

        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        user_service = UserService(db)
        return await user_service.get_by_id(user_id)


optional_auth = OptionalAuth()
