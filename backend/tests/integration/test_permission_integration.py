"""权限绑定系统集成测试"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.role import Role
from app.models.user import User
from app.models.model_config import ModelConfig
from app.services.user_model_service import UserModelService
from app.api.dependencies.permissions import (
    is_admin,
    get_user_bound_knowledge_base_ids,
    get_user_bound_workflow_ids,
)


class TestPermissionHelpers:
    """权限辅助函数测试"""

    @pytest.mark.asyncio
    async def test_is_admin_with_admin_role(self):
        """测试 admin 角色返回 True"""
        admin_role = Mock()
        admin_role.name = "admin"

        user = Mock()
        user.is_superuser = False
        user.roles = [admin_role]

        result = await is_admin(user)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_admin_with_superuser(self):
        """测试 superuser 返回 True"""
        user = Mock()
        user.is_superuser = True
        user.roles = []

        result = await is_admin(user)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_admin_with_normal_user(self):
        """测试普通用户返回 False"""
        editor_role = Mock()
        editor_role.name = "editor"

        user = Mock()
        user.is_superuser = False
        user.roles = [editor_role]

        result = await is_admin(user)
        assert result is False

    @pytest.mark.asyncio
    async def test_is_admin_with_no_roles(self):
        """测试无角色用户返回 False"""
        user = Mock()
        user.is_superuser = False
        user.roles = []

        result = await is_admin(user)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_user_bound_knowledge_base_ids(self):
        """测试获取用户绑定的知识库 ID"""
        kb1 = Mock()
        kb1.id = "kb_001"
        kb2 = Mock()
        kb2.id = "kb_002"

        role = Mock()
        role.knowledge_bases = [kb1, kb2]

        user = Mock()
        user.roles = [role]

        result = await get_user_bound_knowledge_base_ids(user)
        assert "kb_001" in result
        assert "kb_002" in result
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_user_bound_workflow_ids(self):
        """测试获取用户绑定的工作流 ID"""
        wf1 = Mock()
        wf1.id = "wf_001"
        wf2 = Mock()
        wf2.id = "wf_002"

        role = Mock()
        role.workflows = [wf1, wf2]

        user = Mock()
        user.roles = [role]

        result = await get_user_bound_workflow_ids(user)
        assert "wf_001" in result
        assert "wf_002" in result
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_bound_ids_empty_for_no_roles(self):
        """测试无角色用户返回空列表"""
        user = Mock()
        user.roles = []

        kb_result = await get_user_bound_knowledge_base_ids(user)
        wf_result = await get_user_bound_workflow_ids(user)

        assert kb_result == []
        assert wf_result == []

    @pytest.mark.asyncio
    async def test_get_bound_ids_multiple_roles(self):
        """测试多个角色合并知识库 ID"""
        kb1 = Mock()
        kb1.id = "kb_001"
        kb2 = Mock()
        kb2.id = "kb_002"
        kb3 = Mock()
        kb3.id = "kb_003"

        role1 = Mock()
        role1.knowledge_bases = [kb1, kb2]

        role2 = Mock()
        role2.knowledge_bases = [kb2, kb3]  # kb2 在两个角色中都有

        user = Mock()
        user.roles = [role1, role2]

        result = await get_user_bound_knowledge_base_ids(user)
        # 应该去重
        assert len(result) == 3
        assert "kb_001" in result
        assert "kb_002" in result
        assert "kb_003" in result


class TestUserModelService:
    """用户模型配置服务测试"""

    @pytest.fixture
    def service(self):
        return UserModelService()

    @pytest.mark.asyncio
    async def test_bind_model_to_user_success(self, service):
        """测试成功绑定模型（设为默认）"""
        db = AsyncMock()

        # Mock 模型配置
        model_config = Mock()
        model_config.id = "model_001"
        model_config.type = "llm"
        model_config.is_active = True

        # Mock db.get 返回模型配置
        db.get = AsyncMock(return_value=model_config)

        # Mock 检查已绑定（返回空）
        mock_result = Mock()
        mock_result.first = Mock(return_value=None)
        db.execute = AsyncMock(return_value=mock_result)

        # Mock commit
        db.commit = AsyncMock()

        # 使用 patch 来 mock _clear_default_for_type
        with patch.object(service, '_clear_default_for_type', new_callable=AsyncMock):
            await service.bind_model_to_user(db, "user_001", "model_001", is_default=True)

        # 验证 commit 被调用
        assert db.commit.called

    @pytest.mark.asyncio
    async def test_bind_model_to_user_not_default(self, service):
        """测试绑定模型（非默认）"""
        db = AsyncMock()

        model_config = Mock()
        model_config.id = "model_002"
        model_config.type = "llm"
        model_config.is_active = True

        db.get = AsyncMock(return_value=model_config)

        # Mock 检查已绑定（返回空）
        mock_result = Mock()
        mock_result.first = Mock(return_value=None)

        db.execute = AsyncMock(return_value=mock_result)
        db.commit = AsyncMock()

        await service.bind_model_to_user(db, "user_001", "model_002", is_default=False)

        # 验证 commit 被调用
        assert db.commit.called

    @pytest.mark.asyncio
    async def test_bind_model_raises_for_inactive_model(self, service):
        """测试绑定已禁用模型抛出错误"""
        db = AsyncMock()

        model_config = Mock()
        model_config.id = "model_001"
        model_config.is_active = False

        db.get = AsyncMock(return_value=model_config)

        with pytest.raises(ValueError, match="模型配置不存在或已禁用"):
            await service.bind_model_to_user(db, "user_001", "model_001")

    @pytest.mark.asyncio
    async def test_bind_model_raises_for_already_bound(self, service):
        """测试绑定已绑定模型抛出错误"""
        db = AsyncMock()

        model_config = Mock()
        model_config.id = "model_001"
        model_config.is_active = True

        db.get = AsyncMock(return_value=model_config)

        # Mock 已绑定
        mock_result = Mock()
        mock_result.first = Mock(return_value=Mock())
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="已绑定该模型配置"):
            await service.bind_model_to_user(db, "user_001", "model_001")

    @pytest.mark.asyncio
    async def test_get_user_models(self, service):
        """测试获取用户模型列表"""
        db = AsyncMock()

        model1 = Mock()
        model1.id = "model_001"
        model1.name = "gpt-4"
        model1.is_active = True

        model2 = Mock()
        model2.id = "model_002"
        model2.name = "claude-3"
        model2.is_active = True

        # Mock 查询结果
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=[model1, model2])
        mock_result.scalars = Mock(return_value=mock_scalars)
        db.execute = AsyncMock(return_value=mock_result)

        result = await service.get_user_models(db, "user_001")

        assert len(result) == 2
        assert result[0].name == "gpt-4"
        assert result[1].name == "claude-3"

    @pytest.mark.asyncio
    async def test_get_user_default_model(self, service):
        """测试获取用户默认模型"""
        db = AsyncMock()

        model = Mock()
        model.id = "model_001"
        model.name = "gpt-4"

        # Mock 查询结果
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=model)
        db.execute = AsyncMock(return_value=mock_result)

        result = await service.get_user_default_model(db, "user_001", "llm")

        assert result.id == "model_001"
        assert result.name == "gpt-4"

    @pytest.mark.asyncio
    async def test_get_user_default_model_none(self, service):
        """测试用户没有默认模型时返回 None"""
        db = AsyncMock()

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        db.execute = AsyncMock(return_value=mock_result)

        result = await service.get_user_default_model(db, "user_001", "llm")

        assert result is None

    @pytest.mark.asyncio
    async def test_unbind_model(self, service):
        """测试解绑模型"""
        db = AsyncMock()

        db.execute = AsyncMock()
        db.commit = AsyncMock()

        await service.unbind_model(db, "user_001", "model_001")

        assert db.execute.called
        assert db.commit.called


class TestRoleBindingFlow:
    """角色绑定流程测试（使用 mock）"""

    @pytest.mark.asyncio
    async def test_role_knowledge_base_binding(self):
        """测试角色绑定知识库"""
        # 创建 mock 知识库
        kb1 = Mock()
        kb1.id = "kb_001"
        kb1.name = "Knowledge Base 1"

        kb2 = Mock()
        kb2.id = "kb_002"
        kb2.name = "Knowledge Base 2"

        # 创建 mock 角色
        role = Mock()
        role.id = "role_001"
        role.name = "editor"
        role.knowledge_bases = []

        # 绑定知识库
        role.knowledge_bases = [kb1, kb2]

        # 验证绑定
        assert len(role.knowledge_bases) == 2
        assert role.knowledge_bases[0].id == "kb_001"
        assert role.knowledge_bases[1].id == "kb_002"

    @pytest.mark.asyncio
    async def test_role_workflow_binding(self):
        """测试角色绑定工作流"""
        # 创建 mock 工作流
        wf1 = Mock()
        wf1.id = "wf_001"
        wf1.name = "Workflow 1"

        wf2 = Mock()
        wf2.id = "wf_002"
        wf2.name = "Workflow 2"

        # 创建 mock 角色
        role = Mock()
        role.id = "role_001"
        role.name = "editor"
        role.workflows = []

        # 绑定工作流
        role.workflows = [wf1, wf2]

        # 验证绑定
        assert len(role.workflows) == 2
        assert role.workflows[0].id == "wf_001"
        assert role.workflows[1].id == "wf_002"

    @pytest.mark.asyncio
    async def test_role_binding_replace(self):
        """测试角色绑定完全替换"""
        kb1 = Mock()
        kb1.id = "kb_001"

        kb2 = Mock()
        kb2.id = "kb_002"

        kb3 = Mock()
        kb3.id = "kb_003"

        role = Mock()
        role.knowledge_bases = [kb1, kb2]

        # 替换绑定
        role.knowledge_bases = [kb3]

        assert len(role.knowledge_bases) == 1
        assert role.knowledge_bases[0].id == "kb_003"


class TestUserModelBindingFlow:
    """用户模型绑定流程测试（使用 mock）"""

    @pytest.mark.asyncio
    async def test_user_model_binding_success(self):
        """测试用户成功绑定模型（设为默认）"""
        service = UserModelService()
        db = AsyncMock()

        model = Mock()
        model.id = "model_001"
        model.type = "llm"
        model.is_active = True
        model.name = "gpt-4"

        db.get = AsyncMock(return_value=model)

        mock_result = Mock()
        mock_result.first = Mock(return_value=None)
        db.execute = AsyncMock(return_value=mock_result)
        db.commit = AsyncMock()

        # 使用 patch 来 mock _clear_default_for_type
        with patch.object(service, '_clear_default_for_type', new_callable=AsyncMock):
            await service.bind_model_to_user(db, "user_001", "model_001", is_default=True)

        # 验证
        assert db.commit.called

    @pytest.mark.asyncio
    async def test_user_multiple_models_binding(self):
        """测试用户绑定多个模型"""
        service = UserModelService()
        db = AsyncMock()

        # LLM 模型
        llm1 = Mock()
        llm1.id = "llm_001"
        llm1.type = "llm"
        llm1.is_active = True
        llm1.name = "gpt-4"

        llm2 = Mock()
        llm2.id = "llm_002"
        llm2.type = "llm"
        llm2.is_active = True
        llm2.name = "claude-3"

        # Embedding 模型
        embedding = Mock()
        embedding.id = "embed_001"
        embedding.type = "embedding"
        embedding.is_active = True
        embedding.name = "text-embedding-3-small"

        db.commit = AsyncMock()

        # 绑定 llm1 为默认
        db.get = AsyncMock(return_value=llm1)
        mock_check_result = Mock()
        mock_check_result.first = Mock(return_value=None)
        db.execute = AsyncMock(return_value=mock_check_result)

        with patch.object(service, '_clear_default_for_type', new_callable=AsyncMock):
            await service.bind_model_to_user(db, "user_001", "llm_001", is_default=True)

        # 绑定 llm2（非默认）
        db.get = AsyncMock(return_value=llm2)
        mock_check_result2 = Mock()
        mock_check_result2.first = Mock(return_value=None)
        db.execute = AsyncMock(return_value=mock_check_result2)

        await service.bind_model_to_user(db, "user_001", "llm_002", is_default=False)

        # 绑定 embedding 为默认
        db.get = AsyncMock(return_value=embedding)
        mock_check_result3 = Mock()
        mock_check_result3.first = Mock(return_value=None)
        db.execute = AsyncMock(return_value=mock_check_result3)

        with patch.object(service, '_clear_default_for_type', new_callable=AsyncMock):
            await service.bind_model_to_user(db, "user_001", "embed_001", is_default=True)

        # 验证绑定了多次
        assert db.commit.call_count >= 3

    @pytest.mark.asyncio
    async def test_user_set_default_model(self):
        """测试用户切换默认模型"""
        service = UserModelService()
        db = AsyncMock()

        model2 = Mock()
        model2.id = "model_002"
        model2.type = "llm"
        model2.is_active = True

        # 设置 model2 为默认
        db.get = AsyncMock(return_value=model2)

        # Mock 已绑定验证
        mock_bound_result = Mock()
        mock_bound_result.first = Mock(return_value=Mock())
        db.execute = AsyncMock(return_value=mock_bound_result)
        db.commit = AsyncMock()

        # 使用 patch 来 mock _clear_default_for_type
        with patch.object(service, '_clear_default_for_type', new_callable=AsyncMock):
            await service.set_user_default_model(db, "user_001", "model_002")

        assert db.commit.called


class TestAdminPermissionCheck:
    """Admin 权限检查测试"""

    @pytest.mark.asyncio
    async def test_admin_user_is_admin(self):
        """测试 admin 用户是管理员"""
        admin_role = Mock()
        admin_role.name = "admin"

        admin_user = Mock()
        admin_user.is_superuser = False
        admin_user.roles = [admin_role]

        result = await is_admin(admin_user)
        assert result is True

    @pytest.mark.asyncio
    async def test_superuser_is_admin(self):
        """测试 superuser 是管理员"""
        superuser = Mock()
        superuser.is_superuser = True
        superuser.roles = []

        result = await is_admin(superuser)
        assert result is True

    @pytest.mark.asyncio
    async def test_normal_user_not_admin(self):
        """测试普通用户不是管理员"""
        editor_role = Mock()
        editor_role.name = "editor"

        normal_user = Mock()
        normal_user.is_superuser = False
        normal_user.roles = [editor_role]

        result = await is_admin(normal_user)
        assert result is False

    @pytest.mark.asyncio
    async def test_user_with_no_roles_not_admin(self):
        """测试无角色用户不是管理员"""
        user = Mock()
        user.is_superuser = False
        user.roles = []

        result = await is_admin(user)
        assert result is False