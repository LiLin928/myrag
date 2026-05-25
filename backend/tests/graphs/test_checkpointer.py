# backend/tests/graphs/test_checkpointer.py

import pytest


def test_checkpointer_module_imports():
    """测试模块可以正确导入"""
    from app.graphs.checkpointer import get_checkpointer, close_checkpointer, get_connection_pool
    assert get_checkpointer is not None
    assert close_checkpointer is not None
    assert get_connection_pool is not None


def test_checkpointer_function_signatures():
    """测试函数签名正确"""
    from app.graphs.checkpointer import get_checkpointer, close_checkpointer, get_connection_pool

    # 检查函数是可调用的
    assert callable(get_checkpointer)
    assert callable(close_checkpointer)
    assert callable(get_connection_pool)


def test_config_integration():
    """测试配置集成"""
    from app.graphs.checkpointer import settings
    assert settings is not None
    assert hasattr(settings, 'DATABASE_URL')
    assert settings.DATABASE_URL  # DATABASE_URL 不为空


@pytest.mark.skipif(
    True,  # 默认跳过，需要真实数据库时设置为 False
    reason="需要真实 PostgreSQL 数据库连接"
)
@pytest.mark.asyncio
async def test_checkpointer_setup():
    """测试 Checkpointer setup 创建必要的表（需要真实数据库）"""
    from app.graphs.checkpointer import get_checkpointer
    checkpointer = get_checkpointer()
    await checkpointer.setup()
    assert True  # setup 成功不抛异常


@pytest.mark.skipif(
    True,  # 默认跳过，需要真实数据库时设置为 False
    reason="需要真实 PostgreSQL 数据库连接"
)
@pytest.mark.asyncio
async def test_checkpointer_save_and_load():
    """测试状态保存和加载（需要真实数据库）"""
    from app.graphs.checkpointer import get_checkpointer
    checkpointer = get_checkpointer()

    thread_id = "test-thread-001"
    config = {"configurable": {"thread_id": thread_id}}

    # 保存状态
    test_state = {"messages": ["hello", "world"], "step": 1}
    await checkpointer.save(thread_id, test_state, "test-checkpoint")

    # 加载状态
    loaded = await checkpointer.load(thread_id)
    assert loaded is not None
    assert loaded["state"]["messages"] == ["hello", "world"]
    assert loaded["state"]["step"] == 1