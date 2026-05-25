"""权限辅助函数测试"""

import pytest
from unittest.mock import Mock
from app.api.dependencies.permissions import (
    is_admin,
    get_user_bound_knowledge_base_ids,
    get_user_bound_workflow_ids,
)


class TestPermissionHelpers:
    """权限辅助函数测试"""

    @pytest.mark.asyncio
    async def test_is_admin_returns_true_for_admin_role(self):
        """测试 admin 角色返回 True"""
        user = Mock(is_superuser=False)
        admin_role = Mock()
        admin_role.name = "admin"
        user.roles = [admin_role]
        result = await is_admin(user)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_admin_returns_false_for_non_admin(self):
        """测试非 admin 角色返回 False"""
        user = Mock(is_superuser=False)
        editor_role = Mock()
        editor_role.name = "editor"
        user.roles = [editor_role]
        result = await is_admin(user)
        assert result is False

    @pytest.mark.asyncio
    async def test_is_admin_returns_true_for_superuser(self):
        """测试 superuser 返回 True"""
        user = Mock(is_superuser=True, roles=[])
        result = await is_admin(user)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_user_bound_knowledge_base_ids(self):
        """测试获取用户绑定的知识库 ID"""
        user = Mock(is_superuser=False)
        role = Mock()
        kb1 = Mock(id="kb_001")
        kb2 = Mock(id="kb_002")
        role.knowledge_bases = [kb1, kb2]
        user.roles = [role]

        result = await get_user_bound_knowledge_base_ids(user)
        assert "kb_001" in result
        assert "kb_002" in result

    @pytest.mark.asyncio
    async def test_get_user_bound_workflow_ids(self):
        """测试获取用户绑定的工作流 ID"""
        user = Mock(is_superuser=False)
        role = Mock()
        wf1 = Mock(id="wf_001")
        role.workflows = [wf1]
        user.roles = [role]

        result = await get_user_bound_workflow_ids(user)
        assert "wf_001" in result

    @pytest.mark.asyncio
    async def test_get_bound_ids_returns_empty_for_no_roles(self):
        """测试无角色用户返回空列表"""
        user = Mock(is_superuser=False, roles=[])

        kb_result = await get_user_bound_knowledge_base_ids(user)
        wf_result = await get_user_bound_workflow_ids(user)

        assert kb_result == []
        assert wf_result == []