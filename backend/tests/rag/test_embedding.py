# backend/tests/rag/test_embedding.py

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.rag.embedding.embedding_service import EmbeddingService, get_embedding_service
from app.rag.embedding.embedding_models import EmbeddingModelConfig


@pytest.mark.asyncio
async def test_embedding_service_init():
    """测试嵌入服务初始化"""
    config = EmbeddingModelConfig()
    service = EmbeddingService(config)

    assert service is not None
    assert service.config.dimension == 1536


@pytest.mark.asyncio
async def test_embed_text_no_api_key():
    """测试无 API Key 时返回空向量"""
    config = EmbeddingModelConfig(api_key=None)
    service = EmbeddingService(config)

    embedding = await service.embed_text("test text")

    assert embedding is not None
    assert len(embedding) == 1536
    assert all(v == 0.0 for v in embedding)


@pytest.mark.asyncio
async def test_embed_batch_no_api_key():
    """测试批量嵌入无 API Key"""
    config = EmbeddingModelConfig(batch_size=10, api_key=None)
    service = EmbeddingService(config)

    texts = ["text1", "text2", "text3", "text4", "text5"]
    embeddings = await service.embed_batch(texts)

    assert len(embeddings) == 5
    assert all(len(e) == 1536 for e in embeddings)


@pytest.mark.asyncio
async def test_cache_embedding():
    """测试嵌入缓存"""
    config = EmbeddingModelConfig(enable_cache=True, api_key=None)
    service = EmbeddingService(config)

    # 首次嵌入
    embedding1 = await service.embed_text("test")

    # 再次嵌入（应该使用缓存）
    embedding2 = await service.embed_text("test")

    assert embedding1 == embedding2
    assert service.get_cache_size() == 1


@pytest.mark.asyncio
async def test_clear_cache():
    """测试清空缓存"""
    config = EmbeddingModelConfig(enable_cache=True, api_key=None)
    service = EmbeddingService(config)

    await service.embed_text("test")
    assert service.get_cache_size() == 1

    service.clear_cache()
    assert service.get_cache_size() == 0


def test_get_embedding_service():
    """测试获取嵌入服务实例"""
    service = get_embedding_service()
    assert service is not None
    assert isinstance(service, EmbeddingService)