"""ARQ 后台任务模块"""

from arq import create_pool
from arq.connections import RedisSettings

from app.config import get_settings
from app.tasks.document_tasks import (
    parse_document,
    vectorize_chunks,
    chunk_document,
    process_document_full,
    vectorize_single_chunk,
    parse_knowledge_document,
)
from app.tasks.progress_tracker import (
    track_progress,
    notify_task_complete,
    notify_task_failed,
)

settings = get_settings()


class WorkerSettings:
    """ARQ Worker 配置

    在 Redis 启动 Worker:
        arq app.tasks.WorkerSettings
    """

    functions = [
        parse_document,
        vectorize_chunks,
        chunk_document,
        process_document_full,
        vectorize_single_chunk,
        parse_knowledge_document,
    ]

    cron_jobs = []  # 定时任务（后续添加）

    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
    )

    max_jobs = 10
    job_timeout = 600  # 10 分钟超时（MinerU 可能耗时较长）
    keep_result = 3600  # 结果保留 1 小时

    async def on_startup(ctx):
        """Worker 启动钩子"""
        print("ARQ Worker started")

    async def on_shutdown(ctx):
        """Worker 关闭钩子"""
        print("ARQ Worker shutdown")

    async def on_job_start(ctx):
        """任务开始钩子"""
        print(f"Job started: {ctx['job_id']}")

    async def on_job_end(ctx):
        """任务结束钩子"""
        print(f"Job ended: {ctx['job_id']}")


async def get_redis_pool():
    """获取 Redis 连接池"""
    return await create_pool(WorkerSettings.redis_settings)


__all__ = [
    "WorkerSettings",
    "get_redis_pool",
    "parse_document",
    "vectorize_chunks",
    "chunk_document",
    "process_document_full",
    "vectorize_single_chunk",
    "parse_knowledge_document",
    "track_progress",
    "notify_task_complete",
    "notify_task_failed",
]