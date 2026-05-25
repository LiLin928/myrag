"""认证服务"""
from typing import Optional
from datetime import timedelta

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_type,
)
from app.config import get_settings
import redis.asyncio as redis

settings = get_settings()


class AuthService:
    """认证服务类"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.token_expire = timedelta(hours=settings.JWT_EXPIRE_HOURS)
        self.refresh_expire = timedelta(days=7)

    async def create_tokens(self, user_id: str) -> dict:
        """创建访问令牌和刷新令牌"""
        access_token = create_access_token(
            subject=user_id, expires_delta=self.token_expire
        )
        refresh_token = create_refresh_token(
            subject=user_id, expires_delta=self.refresh_expire
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int(self.token_expire.total_seconds()),
        }

    async def refresh_access_token(self, refresh_token: str) -> Optional[dict]:
        """使用刷新令牌获取新的访问令牌"""
        # 验证刷新令牌
        payload = decode_token(refresh_token)
        if not payload:
            return None

        token_type = payload.get("type")
        if token_type != "refresh":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        # 检查令牌是否在黑名单中
        if await self.is_token_blacklisted(refresh_token):
            return None

        # 将旧的刷新令牌加入黑名单
        await self.blacklist_token(refresh_token, self.refresh_expire)

        # 创建新令牌
        return await self.create_tokens(user_id)

    async def blacklist_token(self, token: str, expire: timedelta) -> bool:
        """将令牌加入黑名单"""
        token_id = self._get_token_key(token)
        try:
            await self.redis.setex(
                token_id, int(expire.total_seconds()), "blacklisted"
            )
            return True
        except Exception:
            return False

    async def is_token_blacklisted(self, token: str) -> bool:
        """检查令牌是否在黑名单中"""
        token_id = self._get_token_key(token)
        try:
            result = await self.redis.get(token_id)
            return result is not None
        except Exception:
            return False

    async def logout(self, access_token: str, refresh_token: Optional[str] = None):
        """登出，将令牌加入黑名单"""
        # 将访问令牌加入黑名单
        await self.blacklist_token(access_token, self.token_expire)

        # 如果有刷新令牌，也加入黑名单
        if refresh_token:
            await self.blacklist_token(refresh_token, self.refresh_expire)

    def _get_token_key(self, token: str) -> str:
        """生成令牌在 Redis 中的键"""
        # 使用令牌的哈希值作为键，避免存储完整令牌
        import hashlib

        return f"token:blacklist:{hashlib.sha256(token.encode()).hexdigest()}"
