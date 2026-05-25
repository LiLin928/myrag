"""模型配置服务"""

from typing import Optional, List, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_config import ModelConfig, ModelType
from app.utils.crypto import encrypt_api_key, decrypt_api_key, mask_api_key


class ModelService:
    """模型配置服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_model(
        self,
        name: str,
        type: str,  # 接受字符串类型的模型类型
        provider: str,
        api_base: str,
        api_key: str,
        model_name: str,
        created_by: str,
        context_length: Optional[int] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[int] = None,
        dimension: Optional[int] = None,
        batch_size: Optional[int] = None,
        top_k: Optional[int] = None,
        timeout: int = 30,
        extra_config: Optional[dict] = None,
    ) -> ModelConfig:
        """创建模型配置

        Args:
            name: 模型配置名称
            type: 模型类型 (llm/embedding/rerank)
            provider: 提供商
            api_base: API 基础地址
            api_key: API Key (明文，存储前会加密)
            model_name: 模型名称
            created_by: 创建者 ID
            context_length: LLM 上下文长度
            max_tokens: LLM 最大输出 token
            temperature: LLM 温度参数
            dimension: Embedding 维度
            batch_size: Embedding 批处理大小
            top_k: Rerank top_k
            timeout: 超时时间（秒）
            extra_config: 额外配置

        Returns:
            创建的模型配置对象
        """
        # 加密 API Key
        encrypted_api_key = encrypt_api_key(api_key)

        model = ModelConfig(
            name=name,
            type=type,
            provider=provider,
            api_base=api_base,
            api_key=encrypted_api_key,
            model_name=model_name,
            context_length=context_length,
            max_tokens=max_tokens,
            temperature=temperature,
            dimension=dimension,
            batch_size=batch_size,
            top_k=top_k,
            timeout=timeout,
            extra_config=extra_config,
            created_by=created_by,
        )

        self.db.add(model)
        await self.db.commit()
        await self.db.refresh(model)
        return model

    async def list_models(
        self,
        type: Optional[ModelType] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[ModelConfig], int]:
        """获取模型配置列表

        Args:
            type: 按模型类型筛选
            is_active: 按是否启用筛选
            skip: 跳过数量
            limit: 返回数量

        Returns:
            (模型列表, 总数)
        """
        # 构建查询条件
        conditions = []
        if type is not None:
            conditions.append(ModelConfig.type == type)
        if is_active is not None:
            conditions.append(ModelConfig.is_active == is_active)

        # 查询总数
        count_query = select(func.count()).select_from(ModelConfig)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 查询列表
        query = (
            select(ModelConfig)
            .order_by(ModelConfig.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        models = result.scalars().all()

        return list(models), total

    async def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """根据 ID 获取模型配置

        Args:
            model_id: 模型 ID

        Returns:
            模型配置对象或 None
        """
        result = await self.db.execute(
            select(ModelConfig).where(ModelConfig.id == model_id)
        )
        return result.scalar_one_or_none()

    async def update_model(
        self,
        model_id: str,
        name: Optional[str] = None,
        provider: Optional[str] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        context_length: Optional[int] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[int] = None,
        dimension: Optional[int] = None,
        batch_size: Optional[int] = None,
        top_k: Optional[int] = None,
        timeout: Optional[int] = None,
        extra_config: Optional[dict] = None,
    ) -> Optional[ModelConfig]:
        """更新模型配置

        Args:
            model_id: 模型 ID
            name: 模型配置名称
            provider: 提供商
            api_base: API 基础地址
            api_key: API Key (明文，存储前会加密；若包含 "***" 则不更新)
            model_name: 模型名称
            context_length: LLM 上下文长度
            max_tokens: LLM 最大输出 token
            temperature: LLM 温度参数
            dimension: Embedding 维度
            batch_size: Embedding 批处理大小
            top_k: Rerank top_k
            timeout: 超时时间（秒）
            extra_config: 额外配置

        Returns:
            更新后的模型配置对象或 None
        """
        model = await self.get_model(model_id)
        if not model:
            return None

        # 更新字段
        if name is not None:
            model.name = name
        if provider is not None:
            model.provider = provider
        if api_base is not None:
            model.api_base = api_base
        # 只有当 api_key 不包含 "***" 时才更新（用户未修改时前端返回遮蔽值）
        if api_key is not None and "***" not in api_key:
            model.api_key = encrypt_api_key(api_key)
        if model_name is not None:
            model.model_name = model_name
        if context_length is not None:
            model.context_length = context_length
        if max_tokens is not None:
            model.max_tokens = max_tokens
        if temperature is not None:
            model.temperature = temperature
        if dimension is not None:
            model.dimension = dimension
        if batch_size is not None:
            model.batch_size = batch_size
        if top_k is not None:
            model.top_k = top_k
        if timeout is not None:
            model.timeout = timeout
        if extra_config is not None:
            model.extra_config = extra_config

        await self.db.commit()
        await self.db.refresh(model)
        return model

    async def delete_model(self, model_id: str) -> bool:
        """删除模型配置

        Args:
            model_id: 模型 ID

        Returns:
            是否删除成功
        """
        model = await self.get_model(model_id)
        if not model:
            return False

        await self.db.delete(model)
        await self.db.commit()
        return True

    async def get_default_model(self, type: ModelType) -> Optional[ModelConfig]:
        """获取指定类型的默认模型

        Args:
            type: 模型类型

        Returns:
            默认模型配置对象或 None
        """
        result = await self.db.execute(
            select(ModelConfig)
            .where(and_(ModelConfig.type == type, ModelConfig.is_default == True))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def set_default_model(self, model_id: str) -> Optional[ModelConfig]:
        """设置模型为默认模型

        会自动取消同一类型下其他模型的默认状态

        Args:
            model_id: 模型 ID

        Returns:
            设置后的模型配置对象或 None
        """
        model = await self.get_model(model_id)
        if not model:
            return None

        # 取消同类型其他模型的默认状态
        result = await self.db.execute(
            select(ModelConfig)
            .where(
                and_(
                    ModelConfig.type == model.type,
                    ModelConfig.is_default == True,
                    ModelConfig.id != model_id,
                )
            )
        )
        old_defaults = result.scalars().all()
        for old_default in old_defaults:
            old_default.is_default = False

        # 设置当前模型为默认
        model.is_default = True

        await self.db.commit()
        await self.db.refresh(model)
        return model

    async def toggle_active(self, model_id: str) -> Optional[ModelConfig]:
        """切换模型启用状态

        Args:
            model_id: 模型 ID

        Returns:
            更新后的模型配置对象或 None
        """
        model = await self.get_model(model_id)
        if not model:
            return None

        model.is_active = not model.is_active

        await self.db.commit()
        await self.db.refresh(model)
        return model

    def mask_model_api_key(self, model: ModelConfig) -> dict:
        """返回带有遮蔽 API Key 的模型字典

        用于前端展示，避免泄露完整 API Key

        Args:
            model: 模型配置对象

        Returns:
            包含遮蔽 API Key 的模型字典
        """
        model_dict = {
            "id": model.id,
            "name": model.name,
            "type": model.type,  # 直接使用字符串值
            "provider": model.provider,
            "api_base": model.api_base,
            "api_key": mask_api_key(decrypt_api_key(model.api_key)),
            "model_name": model.model_name,
            "context_length": model.context_length,
            "max_tokens": model.max_tokens,
            "temperature": model.temperature,
            "dimension": model.dimension,
            "batch_size": model.batch_size,
            "top_k": model.top_k,
            "timeout": model.timeout,
            "extra_config": model.extra_config,
            "is_active": model.is_active,
            "is_default": model.is_default,
            "created_by": model.created_by,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }
        return model_dict