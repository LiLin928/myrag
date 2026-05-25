"""用户模型配置服务测试"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.services.user_model_service import UserModelService


class TestUserModelService:
    """用户模型配置服务测试"""

    @pytest.fixture
    def service(self):
        return UserModelService()

    def test_service_creation(self):
        """测试服务创建"""
        service = UserModelService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_bind_model_to_user(self, service):
        """测试绑定模型到用户"""
        db = AsyncMock()
        model_config = Mock(id="model_001", type="llm", is_active=True)
        db.get = AsyncMock(return_value=model_config)

        # Mock 检查已绑定
        mock_empty_result = Mock(first=Mock(return_value=None))
        # Mock _clear_default_for_type 中获取 model_ids
        mock_ids_result = Mock(all=Mock(return_value=[]))
        # Mock insert 操作
        mock_insert_result = Mock()

        db.execute = AsyncMock(side_effect=[
            mock_empty_result,  # 检查已绑定
            mock_ids_result,    # 获取同类型模型 IDs
            mock_insert_result,  # insert 操作
        ])
        db.commit = AsyncMock()

        await service.bind_model_to_user(db, "user_001", "model_001", is_default=True)

        # 验证 commit 被调用
        assert db.commit.called

    @pytest.mark.asyncio
    async def test_bind_model_raises_for_inactive_model(self, service):
        """测试绑定已禁用模型抛出错误"""
        db = AsyncMock()
        model_config = Mock(id="model_001", type="llm", is_active=False)
        db.get = AsyncMock(return_value=model_config)

        with pytest.raises(ValueError, match="模型配置不存在或已禁用"):
            await service.bind_model_to_user(db, "user_001", "model_001")

    @pytest.mark.asyncio
    async def test_bind_model_raises_for_already_bound(self, service):
        """测试绑定已绑定模型抛出错误"""
        db = AsyncMock()
        model_config = Mock(id="model_001", type="llm", is_active=True)
        db.get = AsyncMock(return_value=model_config)
        db.execute = AsyncMock(return_value=Mock(first=Mock(return_value=Mock())))

        with pytest.raises(ValueError, match="已绑定该模型配置"):
            await service.bind_model_to_user(db, "user_001", "model_001")

    @pytest.mark.asyncio
    async def test_set_user_default_model(self, service):
        """测试设置默认模型"""
        db = AsyncMock()
        model_config = Mock(id="model_001", type="llm")
        db.get = AsyncMock(return_value=model_config)

        # Mock 已绑定验证
        mock_bound_result = Mock(first=Mock(return_value=Mock()))
        # Mock _clear_default_for_type 中获取 model_ids
        mock_ids_result = Mock(all=Mock(return_value=[("model_001",)]))
        # Mock update 操作
        mock_update_result = Mock()

        db.execute = AsyncMock(side_effect=[
            mock_bound_result,   # 已绑定验证
            mock_ids_result,     # 获取同类型模型 IDs
            mock_update_result,  # 清除默认
            mock_update_result,  # 设置新的默认
        ])
        db.commit = AsyncMock()

        await service.set_user_default_model(db, "user_001", "model_001")

        assert db.commit.called

    @pytest.mark.asyncio
    async def test_get_user_models(self, service):
        """测试获取用户模型列表"""
        db = AsyncMock()
        model1 = Mock(id="model_001", type="llm", is_active=True)
        model2 = Mock(id="model_002", type="embedding", is_active=True)

        db.execute = AsyncMock(return_value=Mock(
            scalars=Mock(return_value=Mock(all=Mock(return_value=[model1, model2])))
        ))

        result = await service.get_user_models(db, "user_001")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_user_default_model(self, service):
        """测试获取用户默认模型"""
        db = AsyncMock()
        model = Mock(id="model_001", type="llm", is_active=True)

        db.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=model)
        ))

        result = await service.get_user_default_model(db, "user_001", "llm")

        assert result.id == "model_001"

    @pytest.mark.asyncio
    async def test_unbind_model(self, service):
        """测试解绑模型"""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()

        await service.unbind_model(db, "user_001", "model_001")

        assert db.commit.called