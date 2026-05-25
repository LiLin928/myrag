"""用户服务"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security import get_password_hash, verify_password


class UserService:
    """用户服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(self, skip: int = 0, limit: int = 20) -> tuple[List[User], int]:
        """获取用户列表（分页）"""
        from sqlalchemy import func

        # 查询总数
        count_query = select(func.count()).select_from(User)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 查询列表
        query = (
            select(User)
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        users = result.scalars().all()

        return list(users), total

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
    ) -> User:
        """创建用户"""
        user = User(
            username=username,
            email=email,
            password_hash=get_password_hash(password),
            full_name=full_name,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """根据 ID 获取用户"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """验证用户凭证"""
        user = await self.get_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    async def update_user(
        self,
        user_id: str,
        full_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> Optional[User]:
        """更新用户信息"""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        if full_name is not None:
            user.full_name = full_name
        if avatar_url is not None:
            user.avatar_url = avatar_url

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> bool:
        """修改密码"""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        if not verify_password(old_password, user.password_hash):
            return False

        user.password_hash = get_password_hash(new_password)
        await self.db.commit()
        return True

    async def deactivate_user(self, user_id: str) -> bool:
        """停用用户"""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        user.is_active = False
        await self.db.commit()
        return True

    async def activate_user(self, user_id: str) -> bool:
        """激活用户"""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        user.is_active = True
        await self.db.commit()
        return True