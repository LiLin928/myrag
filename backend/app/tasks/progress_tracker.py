"""ARQ 任务进度追踪

追踪 ARQ 后台任务进度，通过 WebSocket 推送给用户
"""

from typing import Dict, Any, Optional
from datetime import datetime
from app.middleware.websocket import manager


async def track_progress(
    job_id: str,
    user_id: str,
    stage: str,
    progress: int,
    message: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
):
    """追踪 ARQ 任务进度并推送到 WebSocket

    Args:
        job_id: 任务 ID
        user_id: 用户 ID（用于推送）
        stage: 当前阶段名称
        progress: 进度百分比 (0-100)
        message: 进度消息（可选）
        extra: 额外信息（可选）
    """
    event = {
        "type": "task_progress",
        "job_id": job_id,
        "stage": stage,
        "progress": min(max(progress, 0), 100),  # 确保在 0-100 范围内
        "message": message,
        "extra": extra or {},
    }

    await manager.send_progress(user_id, event)


async def notify_task_complete(
    job_id: str,
    user_id: str,
    result: Dict[str, Any],
):
    """通知任务完成

    Args:
        job_id: 任务 ID
        user_id: 用户 ID
        result: 任务结果
    """
    event = {
        "type": "task_complete",
        "job_id": job_id,
        "result": result,
        "timestamp": datetime.now().isoformat(),
    }

    await manager.send_progress(user_id, event)


async def notify_task_failed(
    job_id: str,
    user_id: str,
    error: str,
    error_details: Optional[Dict[str, Any]] = None,
):
    """通知任务失败

    Args:
        job_id: 任务 ID
        user_id: 用户 ID
        error: 错误消息
        error_details: 错误详情（可选）
    """
    event = {
        "type": "task_failed",
        "job_id": job_id,
        "error": error,
        "error_details": error_details or {},
        "timestamp": datetime.now().isoformat(),
    }

    await manager.send_progress(user_id, event)