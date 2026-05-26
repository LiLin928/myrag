"""LangGraph PostgreSQL Checkpointer 配置"""

# Windows asyncio 事件循环策略 - 必须在 psycopg_pool 导入之前设置
import sys
import asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from typing import Optional
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

settings = get_settings()

# 全局连接池（懒加载）
_async_pool: Optional[AsyncConnectionPool] = None
_async_checkpointer: Optional[AsyncPostgresSaver] = None


def get_async_connection_pool() -> AsyncConnectionPool:
    """获取异步 PostgreSQL 连接池"""
    global _async_pool
    if _async_pool is None:
        _async_pool = AsyncConnectionPool(
            conninfo=settings.DATABASE_URL,
            open=False,  # 不在创建时打开，等待首次使用时打开
            min_size=2,
            max_size=10,
            # 连接最大空闲时间（秒）- 空闲10分钟后关闭
            max_idle=600,
            # 连接最大使用时间（秒）- 1小时后重置
            max_lifetime=3600,
            # 重连超时（秒）
            reconnect_timeout=30,
        )
    return _async_pool


def get_checkpointer() -> AsyncPostgresSaver:
    """获取 LangGraph 异步 PostgreSQL Checkpointer

    用于持久化 LangGraph 状态机的执行状态，
    支持中断恢复、状态追踪。

    注意：首次使用前需要调用 setup() 创建数据库表。

    Returns:
        AsyncPostgresSaver: LangGraph 异步 Checkpointer 实例
    """
    global _async_checkpointer
    if _async_checkpointer is None:
        pool = get_async_connection_pool()
        _async_checkpointer = AsyncPostgresSaver(pool)
    return _async_checkpointer


async def ensure_pool_open():
    """确保连接池已打开"""
    global _async_pool
    if _async_pool is None:
        _async_pool = get_async_connection_pool()

    if not _async_pool._opened:
        try:
            await _async_pool.open()
            logger.info("PostgreSQL connection pool opened")
        except Exception as e:
            logger.error(f"Failed to open connection pool: {e}")
            raise


async def setup_checkpointer():
    """初始化 Checkpointer 表"""
    global _async_pool
    try:
        # 先确保连接池打开
        await ensure_pool_open()

        checkpointer = get_checkpointer()
        await checkpointer.setup()
        logger.info("LangGraph checkpointer tables initialized")
    except Exception as e:
        logger.warning(f"Checkpointer setup failed: {e}")


async def close_checkpointer():
    """关闭 Checkpointer 和连接池"""
    global _async_pool, _async_checkpointer
    if _async_pool is not None:
        try:
            await _async_pool.close()
            logger.info("PostgreSQL connection pool closed")
        except Exception as e:
            logger.warning(f"Error closing pool: {e}")
        _async_pool = None
        _async_checkpointer = None


# 别名，保持 API 兼容性
get_connection_pool = get_async_connection_pool