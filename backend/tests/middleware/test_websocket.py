# backend/tests/middleware/test_websocket.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.middleware.websocket import ConnectionManager


@pytest.mark.asyncio
async def test_connection_manager_init():
    """测试 ConnectionManager 初始化"""
    manager = ConnectionManager()
    assert manager.active_connections == {}
    assert manager.user_connections == {}


@pytest.mark.asyncio
async def test_connect_user():
    """测试用户连接"""
    manager = ConnectionManager()
    websocket = AsyncMock()
    user_id = "user-001"

    await manager.connect(websocket, user_id)

    assert user_id in manager.active_connections
    assert websocket in manager.active_connections[user_id]


@pytest.mark.asyncio
async def test_disconnect_user():
    """测试用户断开连接"""
    manager = ConnectionManager()
    websocket = AsyncMock()
    user_id = "user-001"

    await manager.connect(websocket, user_id)
    manager.disconnect(websocket, user_id)

    assert user_id not in manager.active_connections or \
           len(manager.active_connections[user_id]) == 0


@pytest.mark.asyncio
async def test_send_progress():
    """测试发送进度事件"""
    manager = ConnectionManager()
    websocket1 = AsyncMock()
    websocket2 = AsyncMock()
    user_id = "user-001"

    await manager.connect(websocket1, user_id)
    await manager.connect(websocket2, user_id)

    event = {
        "type": "task_progress",
        "job_id": "job-001",
        "stage": "parsing",
        "progress": 50,
    }

    await manager.send_progress(user_id, event)

    # 验证两个连接都收到消息
    websocket1.send_text.assert_called_once()
    websocket2.send_text.assert_called_once()

    # 验证消息内容
    import json
    call_args = websocket1.send_text.call_args[0][0]
    parsed = json.loads(call_args)
    assert parsed["type"] == "task_progress"
    assert parsed["job_id"] == "job-001"


@pytest.mark.asyncio
async def test_broadcast():
    """测试广播消息"""
    manager = ConnectionManager()
    websocket1 = AsyncMock()
    websocket2 = AsyncMock()

    await manager.connect(websocket1, "user-001")
    await manager.connect(websocket2, "user-002")

    message = {"type": "system", "content": "server restart"}

    await manager.broadcast(message)

    websocket1.send_text.assert_called_once()
    websocket2.send_text.assert_called_once()


def test_get_connection_count():
    """测试获取用户连接数量"""
    manager = ConnectionManager()
    websocket = MagicMock()
    user_id = "user-001"

    # 未连接时
    assert manager.get_connection_count(user_id) == 0

    # 添加连接（直接操作数据结构用于测试）
    manager.active_connections[user_id] = {websocket}
    assert manager.get_connection_count(user_id) == 1

    # 添加多个连接
    websocket2 = MagicMock()
    manager.active_connections[user_id].add(websocket2)
    assert manager.get_connection_count(user_id) == 2


def test_get_total_connections():
    """测试获取总连接数量"""
    manager = ConnectionManager()

    # 未连接时
    assert manager.get_total_connections() == 0

    # 添加连接（直接操作数据结构用于测试）
    manager.active_connections["user-001"] = {MagicMock(), MagicMock()}
    manager.active_connections["user-002"] = {MagicMock()}
    assert manager.get_total_connections() == 3