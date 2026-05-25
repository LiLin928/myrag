"""向量嵌入服务

调用 OpenAI 兼容接口生成文本向量：
- 单文本嵌入
- 批量嵌入
- 嵌入缓存
- 支持动态模型配置
- 支持从数据库系统设置获取配置
"""

from typing import List, Optional, Dict
import hashlib
import logging
from openai import AsyncOpenAI

from app.rag.embedding.embedding_models import (
    EmbeddingModelConfig,
    get_embedding_config,
    get_embedding_config_from_db,
)

logger = logging.getLogger(__name__)


class EmbeddingService:
    """向量嵌入服务"""

    def __init__(self, config: EmbeddingModelConfig = None, model_name: str = None):
        """初始化嵌入服务

        Args:
            config: 嵌入模型配置（可选）
            model_name: 模型名称（可选，用于动态获取配置）
        """
        # 优先使用传入的配置，否则根据模型名称获取配置
        if config:
            self.config = config
        elif model_name:
            self.config = get_embedding_config(model_name)
        else:
            self.config = get_embedding_config()

        self._client: Optional[AsyncOpenAI] = None
        self._cache: Dict[str, List[float]] = {}

        # 初始化客户端
        self._init_client()

    def _init_client(self):
        """初始化 OpenAI 客户端"""
        api_key = self.config.api_key
        api_base = self.config.get_api_url()

        if api_key and api_key != "your-openai-key":
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=api_base,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )
        else:
            # 无有效 API Key，尝试使用本地服务
            # 对于 Ollama/BGE 本地模型，可能不需要 API Key
            if self.config.provider in ["ollama", "bge"] and api_base:
                self._client = AsyncOpenAI(
                    api_key="dummy-key",  # 本地服务可能不需要真实 key
                    base_url=api_base,
                    timeout=self.config.timeout,
                    max_retries=self.config.max_retries,
                )

    async def embed_text(self, text: str, model: Optional[str] = None) -> List[float]:
        """嵌入单个文本

        Args:
            text: 文本内容
            model: 可选的模型名称，不指定则使用配置中的默认模型

        Returns:
            向量列表
        """
        # 确定使用的模型
        use_model = model or self.config.model_name

        # 检查缓存
        if self.config.enable_cache:
            cache_key = self._get_cache_key(text, use_model)
            if cache_key in self._cache:
                return self._cache[cache_key]

        # 调用 API
        if not self._client:
            # 无客户端，返回空向量
            embedding = [0.0] * self.config.dimension
            # 缓存空向量
            if self.config.enable_cache:
                self._cache[cache_key] = embedding
            return embedding

        try:
            response = await self._client.embeddings.create(
                model=use_model,
                input=text,
            )

            embedding = response.data[0].embedding

            # 缓存
            if self.config.enable_cache:
                self._cache[cache_key] = embedding

            return embedding

        except Exception as e:
            print(f"Embedding error: {e}")
            return [0.0] * self.config.dimension

    async def embed_batch(self, texts: List[str], model: Optional[str] = None) -> List[List[float]]:
        """批量嵌入文本

        Args:
            texts: 文本列表
            model: 可选的模型名称，不指定则使用配置中的默认模型

        Returns:
            向量列表
        """
        if not texts:
            return []

        # 确定使用的模型
        use_model = model or self.config.model_name

        # 检查缓存
        results = [None] * len(texts)
        uncached_texts = []
        uncached_indices = []

        for i, text in enumerate(texts):
            if self.config.enable_cache:
                cache_key = self._get_cache_key(text, use_model)
                if cache_key in self._cache:
                    results[i] = self._cache[cache_key]
                    continue

            uncached_texts.append(text)
            uncached_indices.append(i)

        # 分批处理未缓存的文本
        batch_size = self.config.batch_size

        for start in range(0, len(uncached_texts), batch_size):
            batch = uncached_texts[start:start + batch_size]
            batch_indices = uncached_indices[start:start + batch_size]

            if not self._client:
                # 无客户端，返回空向量
                batch_embeddings = [[0.0] * self.config.dimension for _ in batch]
                # 缓存空向量
                if self.config.enable_cache:
                    for text, embedding in zip(batch, batch_embeddings):
                        cache_key = self._get_cache_key(text, use_model)
                        self._cache[cache_key] = embedding
            else:
                try:
                    response = await self._client.embeddings.create(
                        model=use_model,
                        input=batch,
                    )

                    batch_embeddings = [item.embedding for item in response.data]

                except Exception as e:
                    print(f"Batch embedding error: {e}")
                    batch_embeddings = [[0.0] * self.config.dimension for _ in batch]

            # 缓存
            if self.config.enable_cache:
                for text, embedding in zip(batch, batch_embeddings):
                    cache_key = self._get_cache_key(text, use_model)
                    self._cache[cache_key] = embedding

            # 填充结果
            for j, embedding in enumerate(batch_embeddings):
                results[batch_indices[j]] = embedding

        return results

    def _get_cache_key(self, text: str, model: Optional[str] = None) -> str:
        """生成缓存键

        Args:
            text: 文本内容
            model: 模型名称（可选）

        Returns:
            缓存键
        """
        use_model = model or self.config.model_name
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"{use_model}:{text_hash}"

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()

    def get_cache_size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)


def create_embedding_service(model_name: str = None, config: EmbeddingModelConfig = None) -> EmbeddingService:
    """创建嵌入服务实例

    Args:
        model_name: 模型名称（如 "BAAI/bge-m3", "text-embedding-3-small"）
        config: 自定义配置

    Returns:
        EmbeddingService 实例
    """
    return EmbeddingService(config=config, model_name=model_name)


# 全局嵌入服务实例（延迟初始化）
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service(model_name: str = None) -> EmbeddingService:
    """获取嵌入服务实例（从环境变量或预定义配置）

    Args:
        model_name: 模型名称（可选）。如果不传，返回全局默认实例

    Returns:
        EmbeddingService 实例
    """
    if model_name:
        # 返回针对特定模型的服务实例
        return create_embedding_service(model_name=model_name)

    # 返回全局默认实例（延迟初始化）
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


async def get_embedding_service_from_db(
    db: "AsyncSession",
    model_name: str = None,
) -> EmbeddingService:
    """从数据库系统设置获取嵌入服务实例

    Args:
        db: 数据库会话
        model_name: 模型名称（可选，优先匹配 model_name）

    Returns:
        EmbeddingService 实例
    """
    # 从数据库获取配置
    config = await get_embedding_config_from_db(db, model_name)

    if config:
        logger.info(f"Creating embedding service from DB config: model={config.model_name}")
        return EmbeddingService(config=config)

    # 如果数据库没有配置，使用环境变量或预定义配置
    logger.warning(f"No embedding config found in DB, using default: {model_name or 'default'}")
    return get_embedding_service(model_name)


async def get_embedding_service_for_task(model_name: str = None) -> EmbeddingService:
    """为 ARQ 任务获取嵌入服务实例

    ARQ 任务没有数据库会话，需要单独创建数据库连接来获取配置。

    Args:
        model_name: 模型名称（可选）

    Returns:
        EmbeddingService 实例
    """
    from app.dependencies import get_db

    # 尝试从数据库获取配置
    try:
        async for db in get_db():
            config = await get_embedding_config_from_db(db, model_name)
            if config:
                logger.info(f"Loaded embedding config for task: model={config.model_name}")
                return EmbeddingService(config=config)
            break  # 只尝试一次

    except Exception as e:
        logger.error(f"Failed to get embedding config from DB for task: {e}")

    # 使用环境变量或预定义配置作为备用
    logger.warning(f"Using fallback embedding config for task: {model_name or 'default'}")
    return get_embedding_service(model_name)