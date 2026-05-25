"""LangGraph PostgreSQL Checkpointer 配置"""

from typing import Optional
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from app.config import get_settings


settings = get_settings()

# 全局连接池（懒加载）
_pool: Optional[ConnectionPool] = None
_checkpointer: Optional[PostgresSaver] = None


def get_connection_pool() -> ConnectionPool:
    """获取 PostgreSQL 连接池"""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=settings.DATABASE_URL,
            open=True,
            min_size=2,
            max_size=10,
        )
    return _pool


def get_checkpointer() -> PostgresSaver:
    """获取 LangGraph PostgreSQL Checkpointer

    用于持久化 LangGraph 状态机的执行状态，
    支持中断恢复、状态追踪。

    注意：首次使用前需要调用 setup() 创建数据库表。

    Returns:
        PostgresSaver: LangGraph Checkpointer 实例
    """
    global _checkpointer
    if _checkpointer is None:
        pool = get_connection_pool()
        _checkpointer = PostgresSaver(pool)
        # 不在此处调用 setup，改为延迟调用
        # _checkpointer.setup() 应在首次使用前由调用方执行
    return _checkpointer


async def close_checkpointer():
    """关闭 Checkpointer 和连接池"""
    global _pool, _checkpointer
    if _pool is not None:
        _pool.close()
        _pool = None
        _checkpointer = None