"""WebSocket 连接管理器

管理用户 WebSocket 连接，支持：
- 用户连接/断开追踪
- 进度事件推送
- 广播消息
"""

from fastapi import WebSocket
from typing import Dict, Set, Any
import json
from datetime import datetime


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 用户连接映射: user_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # WebSocket -> user_id 映射
        self.user_connections: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """建立 WebSocket 连接

        Args:
            websocket: WebSocket 连接对象
            user_id: 用户 ID
        """
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        self.user_connections[websocket] = user_id

    def disconnect(self, websocket: WebSocket, user_id: str):
        """断开 WebSocket 连接

        Args:
            websocket: WebSocket 连接对象
            user_id: 用户 ID
        """
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        if websocket in self.user_connections:
            del self.user_connections[websocket]

    async def send_progress(self, user_id: str, event: Dict[str, Any]):
        """向用户发送进度事件

        Args:
            user_id: 目标用户 ID
            event: 事件数据，包含 type、job_id、stage、progress 等
        """
        if user_id not in self.active_connections:
            return

        message = json.dumps({
            **event,
            "timestamp": datetime.now().isoformat(),
        })

        # 发送给用户的所有连接
        dead_connections = set()
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_text(message)
            except Exception:
                # 连接已断开，标记清理
                dead_connections.add(connection)

        # 清理断开的连接
        for dead in dead_connections:
            self.disconnect(dead, user_id)

    async def broadcast(self, message: Dict[str, Any]):
        """广播消息给所有连接

        Args:
            message: 广播消息内容
        """
        text = json.dumps({
            **message,
            "timestamp": datetime.now().isoformat(),
        })

        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_text(text)
                except Exception:
                    pass

    def get_connection_count(self, user_id: str) -> int:
        """获取用户连接数量"""
        return len(self.active_connections.get(user_id, set()))

    def get_total_connections(self) -> int:
        """获取总连接数量"""
        total = 0
        for connections in self.active_connections.values():
            total += len(connections)
        return total


# 全局连接管理器实例
manager = ConnectionManager()