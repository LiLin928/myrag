"""工作流 WebSocket 路由

提供工作流执行进度实时推送的 WebSocket 端点
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from app.middleware.websocket import manager
from app.db import get_db
from app.workflow.models.execution import WorkflowExecution
from app.workflow.models.workflow_execution_log import WorkflowExecutionLog
from app.api.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter(tags=["workflow-websocket"])


@router.websocket("/ws/workflows/executions/{execution_id}/progress")
async def workflow_execution_progress(
    websocket: WebSocket,
    execution_id: str,
    db: AsyncSession = Depends(get_db),
):
    """工作流执行进度 WebSocket 端点

    客户端连接此端点后，会收到以下事件：
    - execution_start: 执行开始
    - node_start: 节点开始执行
    - node_complete: 节点完成
    - node_error: 节点错误
    - execution_progress: 整体进度更新
    - execution_complete: 执行完成
    - execution_interrupted: 执行中断

    Args:
        execution_id: 执行 ID
    """
    await websocket.accept()

    # 获取执行信息以验证用户
    result = await db.execute(
        select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Execution not found",
        }))
        await websocket.close()
        return

    user_id = str(execution.user_id)

    # 注册到连接管理器
    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_text()

            # 心跳处理
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

    except Exception as e:
        manager.disconnect(websocket, user_id)


@router.get("/ws/workflows/executions/{execution_id}/logs")
async def get_execution_logs(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取执行日志（HTTP fallback）

    Returns:
        执行日志列表
    """
    # First check if execution exists and belongs to current user
    result = await db.execute(
        select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    if execution.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this execution's logs")

    result = await db.execute(
        select(WorkflowExecutionLog)
        .where(WorkflowExecutionLog.execution_id == execution_id)
        .order_by(WorkflowExecutionLog.timestamp)
    )
    logs = result.scalars().all()

    return [
        {
            "id": str(log.id),
            "node_id": log.node_id,
            "node_name": log.node_name,
            "event_type": log.event_type,
            "timestamp": log.timestamp.isoformat(),
            "input_data": log.input_data,
            "output_data": log.output_data,
            "error_message": log.error_message,
            "duration_ms": log.duration_ms,
            "progress_percent": log.progress_percent,
        }
        for log in logs
    ]