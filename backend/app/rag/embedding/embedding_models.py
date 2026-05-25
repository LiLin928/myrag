"""嵌入模型配置

支持多种嵌入模型：
- OpenAI: text-embedding-3-small, text-embedding-3-large
- 其他 OpenAI 兼容接口（DeepSeek、Ollama 等）
- BGE 系列：BAAI/bge-m3, BAAI/bge-large-zh
- 从数据库系统设置获取配置
"""

import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EmbeddingProvider(str, Enum):
    """嵌入模型提供商"""
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"
    BGE = "bge"
    CUSTOM = "custom"


class EmbeddingModelConfig(BaseModel):
    """嵌入模型配置"""

    provider: EmbeddingProvider = Field(default=EmbeddingProvider.OPENAI, description="提供商")
    model_name: str = Field(default="text-embedding-3-small", description="模型名称")
    dimension: int = Field(default=1536, description="向量维度")

    # API 配置
    api_key: Optional[str] = Field(None, description="API Key")
    api_base: Optional[str] = Field(None, description="API Base URL")

    # 性能配置
    batch_size: int = Field(default=100, description="批量处理大小")
    max_retries: int = Field(default=3, description="最大重试次数")
    timeout: int = Field(default=30, description="请求超时（秒）")

    # 缓存配置
    enable_cache: bool = Field(default=True, description="是否启用缓存")
    cache_ttl: int = Field(default=3600, description="缓存过期时间（秒）")

    def get_api_url(self) -> str:
        """获取 API URL

        Returns:
            API Base URL
        """
        if self.api_base:
            return self.api_base

        # 默认 URL
        default_urls = {
            EmbeddingProvider.OPENAI: "https://api.openai.com/v1",
            EmbeddingProvider.DEEPSEEK: "https://api.deepseek.com/v1",
            EmbeddingProvider.OLLAMA: os.getenv("OLLAMA_API_URL", "http://localhost:11434"),
            EmbeddingProvider.BGE: os.getenv("BGE_API_URL", "http://localhost:8000/v1"),
        }

        return default_urls.get(self.provider, "https://api.openai.com/v1")


# 预定义模型配置（作为备用）
DEFAULT_MODELS: Dict[str, EmbeddingModelConfig] = {
    # OpenAI 模型
    "text-embedding-3-small": EmbeddingModelConfig(
        provider=EmbeddingProvider.OPENAI,
        model_name="text-embedding-3-small",
        dimension=1536,
        api_key=os.getenv("OPENAI_API_KEY"),
    ),
    "text-embedding-3-large": EmbeddingModelConfig(
        provider=EmbeddingProvider.OPENAI,
        model_name="text-embedding-3-large",
        dimension=3072,
        api_key=os.getenv("OPENAI_API_KEY"),
    ),
    # DeepSeek 模型
    "deepseek-embedding": EmbeddingModelConfig(
        provider=EmbeddingProvider.DEEPSEEK,
        model_name="deepseek-embedding",
        dimension=1536,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
    ),
    # Ollama 本地模型
    "nomic-embed-text": EmbeddingModelConfig(
        provider=EmbeddingProvider.OLLAMA,
        model_name="nomic-embed-text",
        dimension=768,
    ),
    "bge-m3": EmbeddingModelConfig(
        provider=EmbeddingProvider.OLLAMA,
        model_name="bge-m3",
        dimension=1024,
    ),
    # BGE 系列（本地部署或远程 API）
    "BAAI/bge-m3": EmbeddingModelConfig(
        provider=EmbeddingProvider.BGE,
        model_name="BAAI/bge-m3",
        dimension=1024,
        api_key=os.getenv("BGE_API_KEY"),
        api_base=os.getenv("BGE_API_URL"),
    ),
    "BAAI/bge-large-zh": EmbeddingModelConfig(
        provider=EmbeddingProvider.BGE,
        model_name="BAAI/bge-large-zh",
        dimension=1024,
        api_key=os.getenv("BGE_API_KEY"),
        api_base=os.getenv("BGE_API_URL"),
    ),
}


async def get_embedding_config_from_db(
    db: "AsyncSession",
    model_name: str = None,
) -> Optional[EmbeddingModelConfig]:
    """从数据库获取 embedding 配置

    Args:
        db: 数据库会话
        model_name: 模型名称（可选，优先匹配 model_name）

    Returns:
        EmbeddingModelConfig 或 None
    """
    from sqlalchemy import select, and_
    from app.models.model_config import ModelConfig, ModelType
    from app.utils.crypto import decrypt_api_key

    try:
        # 构建查询条件
        conditions = [ModelConfig.type == ModelType.EMBEDDING, ModelConfig.is_active == True]

        if model_name:
            # 优先按 model_name 匹配
            conditions.append(ModelConfig.model_name == model_name)
        else:
            # 获取默认模型
            conditions.append(ModelConfig.is_default == True)

        query = select(ModelConfig).where(and_(*conditions)).limit(1)
        result = await db.execute(query)
        model_config = result.scalar_one_or_none()

        if not model_config:
            # 如果没有找到默认模型，尝试获取任意一个激活的模型
            query = select(ModelConfig).where(
                and_(ModelConfig.type == ModelType.EMBEDDING, ModelConfig.is_active == True)
            ).limit(1)
            result = await db.execute(query)
            model_config = result.scalar_one_or_none()

        if model_config:
            # 解密 API Key
            api_key = decrypt_api_key(model_config.api_key) if model_config.api_key else None

            # 推断 provider
            provider = _infer_provider(model_config.provider, model_config.api_base)

            config = EmbeddingModelConfig(
                provider=provider,
                model_name=model_config.model_name,
                dimension=model_config.dimension or 1536,
                api_key=api_key,
                api_base=model_config.api_base,
                batch_size=model_config.batch_size or 100,
                timeout=model_config.timeout or 30,
            )
            logger.info(f"Loaded embedding config from DB: model={model_config.model_name}, provider={provider}, dimension={config.dimension}")
            return config

        return None

    except Exception as e:
        logger.error(f"Failed to get embedding config from DB: {e}")
        return None


def _infer_provider(provider_str: str, api_base: str) -> EmbeddingProvider:
    """根据 provider 字符串或 api_base 推断提供商

    Args:
        provider_str: 提供商字符串
        api_base: API 基础地址

    Returns:
        EmbeddingProvider
    """
    provider_lower = provider_str.lower() if provider_str else ""

    if provider_lower in ["openai"]:
        return EmbeddingProvider.OPENAI
    elif provider_lower in ["deepseek"]:
        return EmbeddingProvider.DEEPSEEK
    elif provider_lower in ["ollama"]:
        return EmbeddingProvider.OLLAMA
    elif provider_lower in ["bge", "baai", "bge-m3"]:
        return EmbeddingProvider.BGE
    elif api_base and "11434" in api_base:
        return EmbeddingProvider.OLLAMA
    elif api_base and "deepseek" in api_base:
        return EmbeddingProvider.DEEPSEEK
    else:
        return EmbeddingProvider.CUSTOM


def get_embedding_config(model_name: str = None) -> EmbeddingModelConfig:
    """获取嵌入模型配置（从环境变量或预定义配置）

    注意：此函数不从数据库获取配置。
    在需要从数据库获取配置的场景，请使用 get_embedding_config_from_db。

    Args:
        model_name: 模型名称，如 "text-embedding-3-small", "BAAI/bge-m3"

    Returns:
        EmbeddingModelConfig
    """
    # 优先使用传入的模型名称
    if model_name:
        # 查找预定义配置
        if model_name in DEFAULT_MODELS:
            config = DEFAULT_MODELS[model_name].copy()
            # 确保从环境变量获取最新的 API Key
            if config.provider == EmbeddingProvider.OPENAI:
                config.api_key = os.getenv("OPENAI_API_KEY")
            elif config.provider == EmbeddingProvider.DEEPSEEK:
                config.api_key = os.getenv("DEEPSEEK_API_KEY")
            elif config.provider == EmbeddingProvider.BGE:
                config.api_key = os.getenv("BGE_API_KEY") or os.getenv("OPENAI_API_KEY")
            return config
        else:
            # 未预定义的模型，尝试自动推断
            env_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
            env_api_key = os.getenv("OPENAI_API_KEY")
            env_api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

            # 推断维度
            dimension = 1536  # 默认维度

            return EmbeddingModelConfig(
                provider=EmbeddingProvider.CUSTOM,
                model_name=model_name,
                dimension=dimension,
                api_key=env_api_key,
                api_base=env_api_base,
            )

    # 使用环境变量中的默认模型
    env_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    return get_embedding_config(env_model)