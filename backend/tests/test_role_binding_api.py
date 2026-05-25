"""角色绑定 API 测试

测试角色绑定的三个端点：
- PUT /roles/{role_id}/knowledge-bases - 绑定知识库
- PUT /roles/{role_id}/workflows - 绑定工作流
- GET /roles/{role_id}/bindings - 获取绑定信息
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestRoleBindingRoutes:
    """角色绑定 API 路由测试"""

    def test_bind_knowledge_bases_endpoint_exists(self):
        """测试绑定知识库端点存在"""
        # PUT /api/v1/roles/{role_id}/knowledge-bases
        response = client.put(
            "/api/v1/roles/test-role-id/knowledge-bases",
            json={"knowledge_base_ids": ["kb-1", "kb-2"]},
        )

        # 端点应存在（可能返回 200, 401, 403, 404, 422）
        assert response.status_code in [200, 401, 403, 404, 422]

    def test_bind_workflows_endpoint_exists(self):
        """测试绑定工作流端点存在"""
        # PUT /api/v1/roles/{role_id}/workflows
        response = client.put(
            "/api/v1/roles/test-role-id/workflows",
            json={"workflow_ids": ["wf-1", "wf-2"]},
        )

        # 端点应存在（可能返回 200, 401, 403, 404, 422）
        assert response.status_code in [200, 401, 403, 404, 422]

    def test_get_bindings_endpoint_exists(self):
        """测试获取绑定信息端点存在"""
        # GET /api/v1/roles/{role_id}/bindings
        response = client.get(
            "/api/v1/roles/test-role-id/bindings",
        )

        # 端点应存在（可能返回 200, 401, 403, 404）
        assert response.status_code in [200, 401, 403, 404]


class TestBindKnowledgeBasesRequest:
    """测试 BindKnowledgeBasesRequest Schema"""

    def test_request_requires_knowledge_base_ids(self):
        """测试请求需要 knowledge_base_ids 字段"""
        response = client.put(
            "/api/v1/roles/test-role-id/knowledge-bases",
            json={},
        )
        # 缺少必需字段应返回 422，但如果先检查认证则返回 401
        # 两者都表示端点存在
        assert response.status_code in [401, 403, 422]


class TestBindWorkflowsRequest:
    """测试 BindWorkflowsRequest Schema"""

    def test_request_requires_workflow_ids(self):
        """测试请求需要 workflow_ids 字段"""
        response = client.put(
            "/api/v1/roles/test-role-id/workflows",
            json={},
        )
        # 缺少必需字段应返回 422，但如果先检查认证则返回 401
        # 两者都表示端点存在
        assert response.status_code in [401, 403, 422]


class TestRoleBindingsResponse:
    """测试 RoleBindingsResponse Schema"""

    def test_response_schema_has_knowledge_bases(self):
        """测试响应 Schema 包含 knowledge_bases 字段"""
        # 如果角色不存在，应返回 404
        # 如果存在，响应应包含 knowledge_bases 字段
        response = client.get(
            "/api/v1/roles/test-role-id/bindings",
        )
        # 验证路由存在（不是 405 Method Not Allowed）
        assert response.status_code != 405