"""WebSocket API 路由"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.middleware.websocket import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
):
    """WebSocket 连接端点

    用户通过此端点建立 WebSocket 连接，接收：
    - ARQ 任务进度推送
    - 工作流执行状态更新
    - Agent 对话消息
    - 系统广播消息

    Args:
        user_id: 用户 ID（用于标识连接）
    """
    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_text()

            # 心跳处理
            if data == "ping":
                await websocket.send_text("pong")

            # 可扩展：处理客户端其他消息
            # 例如：订阅特定工作流进度

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

    except Exception:
        # 异常断开
        manager.disconnect(websocket, user_id)


@router.get("/ws/stats")
async def websocket_stats():
    """获取 WebSocket 连接统计

    Returns:
        总连接数、各用户连接数
    """
    return {
        "total_connections": manager.get_total_connections(),
        "users": {
            user_id: manager.get_connection_count(user_id)
            for user_id in manager.active_connections
        }
    }