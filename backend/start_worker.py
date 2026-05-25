"""启动 ARQ Worker

在后台执行文档解析任务。

启动方式:
    python start_worker.py

或者直接使用 arq 命令:
    arq app.tasks.WorkerSettings
"""

import asyncio
import sys
from arq import run_worker
from app.tasks import WorkerSettings


def main():
    """启动 ARQ Worker"""
    print("=" * 60)
    print("MyRAG ARQ Worker")
    print("=" * 60)
    print(f"Redis Host: {WorkerSettings.redis_settings.host}")
    print(f"Redis Port: {WorkerSettings.redis_settings.port}")
    print(f"Max Jobs: {WorkerSettings.max_jobs}")
    print(f"Job Timeout: {WorkerSettings.job_timeout}s")
    print("=" * 60)
    print("\nStarting worker...\n")

    # Windows 需要特殊处理事件循环
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 启动 worker
    run_worker(WorkerSettings)


if __name__ == "__main__":
    main()