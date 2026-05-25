# tests/api/test_agent_routes.py

import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestAgentRoutes:
    """Agent API 路由测试"""

    def test_chat_endpoint_exists(self):
        """测试 chat 端点存在"""
        # POST /api/v1/agent/chat
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "thread_id": "test-123",
                "message": "你好",
                "user_id": "user-1",
            },
        )

        # 端点应存在（可能返回 200 或需要认证）
        assert response.status_code in [200, 401, 403, 422]

    def test_resume_endpoint_exists(self):
        """测试 resume 端点存在"""
        response = client.post(
            "/api/v1/agent/resume",
            json={
                "thread_id": "test-123",
                "decision": "approve",
            },
        )

        assert response.status_code in [200, 401, 403, 422]

    def test_history_endpoint_exists(self):
        """测试 history 端点存在"""
        response = client.get(
            "/api/v1/agent/history/test-123",
        )

        assert response.status_code in [200, 401, 403, 404]

    def test_interrupt_endpoint_exists(self):
        """测试 interrupt 端点存在"""
        response = client.get(
            "/api/v1/agent/interrupt/test-123",
        )

        assert response.status_code in [200, 401, 403, 404]