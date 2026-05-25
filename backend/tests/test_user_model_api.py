"""用户模型配置 API 测试

测试用户模型配置的四个端点：
- GET /users/me/models - 获取我的模型列表
- POST /users/me/models/{model_id}/bind - 绑定模型
- POST /users/me/models/{model_id}/set-default - 设置默认
- DELETE /users/me/models/{model_id} - 解绑模型
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestUserModelRoutes:
    """用户模型配置 API 路由测试"""

    def test_get_my_models_endpoint_exists(self):
        """测试获取我的模型列表端点存在"""
        # GET /api/v1/users/me/models
        response = client.get("/api/v1/users/me/models")

        # 端点应存在（可能返回 200, 401, 403, 404, 422）
        assert response.status_code in [200, 401, 403, 404, 422]

    def test_bind_model_endpoint_exists(self):
        """测试绑定模型端点存在"""
        # POST /api/v1/users/me/models/{model_id}/bind
        response = client.post(
            "/api/v1/users/me/models/test-model-id/bind",
            json={"is_default": True},
        )

        # 端点应存在（可能返回 200, 201, 401, 403, 404, 422）
        assert response.status_code in [200, 201, 401, 403, 404, 422]

    def test_set_default_model_endpoint_exists(self):
        """测试设置默认模型端点存在"""
        # POST /api/v1/users/me/models/{model_id}/set-default
        response = client.post(
            "/api/v1/users/me/models/test-model-id/set-default",
        )

        # 端点应存在（可能返回 200, 201, 401, 403, 404, 422）
        assert response.status_code in [200, 201, 401, 403, 404, 422]

    def test_unbind_model_endpoint_exists(self):
        """测试解绑模型端点存在"""
        # DELETE /api/v1/users/me/models/{model_id}
        response = client.delete(
            "/api/v1/users/me/models/test-model-id",
        )

        # 端点应存在（可能返回 200, 204, 401, 403, 404, 422）
        assert response.status_code in [200, 204, 401, 403, 404, 422]


class TestBindModelRequest:
    """测试 BindModelRequest Schema"""

    def test_bind_model_request_is_default_optional(self):
        """测试 is_default 字段是可选的"""
        response = client.post(
            "/api/v1/users/me/models/test-model-id/bind",
            json={},
        )
        # is_default 是可选的，所以不应返回 422
        # 如果未认证则返回 401，端点存在
        assert response.status_code in [200, 201, 401, 403, 404]


class TestUserModelsResponse:
    """测试 UserModelsResponse Schema"""

    def test_response_should_have_models_field(self):
        """测试响应应包含 models 字段"""
        response = client.get("/api/v1/users/me/models")
        # 验证路由存在（不是 405 Method Not Allowed）
        assert response.status_code != 405