"""用户模型配置服务

管理用户与模型配置的绑定关系：
- 绑定/解绑模型
- 设置默认模型
- 获取用户模型列表
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete

from app.models.model_config import ModelConfig
from app.models.associations import user_model_configs


class UserModelService:
    """用户模型配置服务"""

    async def bind_model_to_user(
        self,
        db: AsyncSession,
        user_id: str,
        model_config_id: str,
        is_default: bool = False
    ) -> None:
        """为用户绑定模型配置

        Args:
            db: 数据库会话
            user_id: 用户 ID
            model_config_id: 模型配置 ID
            is_default: 是否设为默认

        Raises:
            ValueError: 模型不存在、已禁用或已绑定
        """
        # 验证模型配置存在且活跃
        model_config = await db.get(ModelConfig, model_config_id)
        if not model_config or not model_config.is_active:
            raise ValueError("模型配置不存在或已禁用")

        # 检查是否已绑定
        existing = await db.execute(
            select(user_model_configs)
            .where(user_model_configs.c.user_id == user_id)
            .where(user_model_configs.c.model_config_id == model_config_id)
        )
        if existing.first():
            raise ValueError("已绑定该模型配置")

        # 如果设为默认，先清除该类型的其他默认
        if is_default:
            await self._clear_default_for_type(db, user_id, model_config.type)

        # 插入关联
        await db.execute(
            insert(user_model_configs).values(
                user_id=user_id,
                model_config_id=model_config_id,
                is_default=is_default
            )
        )
        await db.commit()

    async def set_user_default_model(
        self,
        db: AsyncSession,
        user_id: str,
        model_config_id: str
    ) -> None:
        """设置用户的默认模型

        Args:
            db: 数据库会话
            user_id: 用户 ID
            model_config_id: 模型配置 ID

        Raises:
            ValueError: 模型不存在或用户未绑定
        """
        model_config = await db.get(ModelConfig, model_config_id)
        if not model_config:
            raise ValueError("模型配置不存在")

        # 验证用户已绑定该模型
        bound = await db.execute(
            select(user_model_configs)
            .where(user_model_configs.c.user_id == user_id)
            .where(user_model_configs.c.model_config_id == model_config_id)
        )
        if not bound.first():
            raise ValueError("用户未绑定该模型配置")

        # 清除该类型的其他默认
        await self._clear_default_for_type(db, user_id, model_config.type)

        # 设置新的默认
        await db.execute(
            update(user_model_configs)
            .where(user_model_configs.c.user_id == user_id)
            .where(user_model_configs.c.model_config_id == model_config_id)
            .values(is_default=True)
        )
        await db.commit()

    async def _clear_default_for_type(
        self,
        db: AsyncSession,
        user_id: str,
        model_type: str
    ) -> None:
        """清除用户某类型模型的默认标记

        Args:
            db: 数据库会话
            user_id: 用户 ID
            model_type: 模型类型（llm/embedding/rerank）
        """
        # 获取该类型所有已绑定的模型配置 ID
        model_ids = await db.execute(
            select(ModelConfig.id)
            .join(user_model_configs)
            .where(user_model_configs.c.user_id == user_id)
            .where(ModelConfig.type == model_type)
        )
        ids = [row[0] for row in model_ids.all()]

        if ids:
            await db.execute(
                update(user_model_configs)
                .where(user_model_configs.c.user_id == user_id)
                .where(user_model_configs.c.model_config_id.in_(ids))
                .values(is_default=False)
            )

    async def get_user_models(
        self,
        db: AsyncSession,
        user_id: str
    ) -> List[ModelConfig]:
        """获取用户绑定的所有模型配置

        Args:
            db: 数据库会话
            user_id: 用户 ID

        Returns:
            模型配置列表
        """
        result = await db.execute(
            select(ModelConfig)
            .join(user_model_configs)
            .where(user_model_configs.c.user_id == user_id)
            .where(ModelConfig.is_active == True)
        )
        return result.scalars().all()

    async def get_user_default_model(
        self,
        db: AsyncSession,
        user_id: str,
        model_type: str
    ) -> Optional[ModelConfig]:
        """获取用户某类型的默认模型

        Args:
            db: 数据库会话
            user_id: 用户 ID
            model_type: 模型类型

        Returns:
            默认模型配置，不存在则返回 None
        """
        result = await db.execute(
            select(ModelConfig)
            .join(user_model_configs)
            .where(user_model_configs.c.user_id == user_id)
            .where(user_model_configs.c.is_default == True)
            .where(ModelConfig.type == model_type)
            .where(ModelConfig.is_active == True)
        )
        return result.scalar_one_or_none()

    async def unbind_model(
        self,
        db: AsyncSession,
        user_id: str,
        model_config_id: str
    ) -> None:
        """解绑模型配置

        Args:
            db: 数据库会话
            user_id: 用户 ID
            model_config_id: 模型配置 ID
        """
        await db.execute(
            delete(user_model_configs)
            .where(user_model_configs.c.user_id == user_id)
            .where(user_model_configs.c.model_config_id == model_config_id)
        )
        await db.commit()


# 全局服务实例
user_model_service = UserModelService()