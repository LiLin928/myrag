# backend/tests/rag/test_embedding_models.py

import pytest
from app.rag.embedding.embedding_models import (
    EmbeddingModelConfig,
    EmbeddingProvider,
    get_embedding_config,
    DEFAULT_MODELS,
)


def test_embedding_config_defaults():
    """测试默认配置"""
    config = EmbeddingModelConfig()

    assert config.provider == EmbeddingProvider.OPENAI
    assert config.model_name == "text-embedding-3-small"
    assert config.dimension == 1536
    assert config.batch_size == 100


def test_get_api_url():
    """测试获取 API URL"""
    # OpenAI 默认
    config = EmbeddingModelConfig()
    url = config.get_api_url()
    assert url == "https://api.openai.com/v1"

    # 自定义 Base
    config = EmbeddingModelConfig(api_base="http://custom.api.com")
    url = config.get_api_url()
    assert url == "http://custom.api.com"


def test_get_embedding_config():
    """测试获取预定义配置"""
    config = get_embedding_config("openai-small")

    assert config.model_name == "text-embedding-3-small"

    config = get_embedding_config("unknown")
    assert config.model_name == "text-embedding-3-small"  # 返回默认


def test_custom_provider():
    """测试自定义提供商"""
    config = EmbeddingModelConfig(
        provider=EmbeddingProvider.CUSTOM,
        model_name="custom-embedding",
        api_base="http://custom.api.com/v1",
        dimension=512,
    )

    assert config.provider == EmbeddingProvider.CUSTOM
    assert config.dimension == 512