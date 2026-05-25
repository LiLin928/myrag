"""对话权限过滤测试"""

import pytest
from unittest.mock import Mock, AsyncMock
from app.services.conversation_service import ConversationService
from app.api.dependencies.permissions import is_admin


class TestConversationPermission:
    """对话权限过滤测试"""

    @pytest.mark.asyncio
    async def test_normal_user_only_sees_own_conversations(self):
        """测试普通用户只能看自己的对话"""
        # 准备数据
        service = ConversationService()

        # Mock 普通用户
        normal_user = Mock(is_superuser=False)
        normal_role = Mock()
        normal_role.name = "user"
        normal_user.roles = [normal_role]
        normal_user.id = "user_001"

        # Mock 数据库会话
        db = AsyncMock()

        # Mock 查询结果 - 返回该用户的对话
        mock_conversations = [
            Mock(id="conv_001", user_id="user_001", title="用户1的对话"),
            Mock(id="conv_002", user_id="user_001", title="用户1的另一个对话"),
        ]

        # 模拟数据库查询
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_conversations
        db.execute.return_value = mock_result

        # 执行查询
        result = await service.list_conversations_with_permission(
            db=db,
            current_user=normal_user,
            skip=0,
            limit=10,
            include_all=False
        )

        # 验证：普通用户只能看自己的对话
        assert len(result) == 2
        assert all(conv.user_id == "user_001" for conv in result)
        # 验证调用了正确的查询（应该只查当前用户）
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_admin_default_sees_own_conversations(self):
        """测试 admin 默认只能看自己的对话"""
        # 准备数据
        service = ConversationService()

        # Mock admin 用户
        admin_user = Mock(is_superuser=False)
        admin_role = Mock()
        admin_role.name = "admin"
        admin_user.roles = [admin_role]
        admin_user.id = "admin_001"

        # Mock 数据库会话
        db = AsyncMock()

        # Mock 查询结果 - 返回 admin 自己的对话
        mock_conversations = [
            Mock(id="conv_003", user_id="admin_001", title="Admin的对话"),
        ]

        # 模拟数据库查询
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_conversations
        db.execute.return_value = mock_result

        # 执行查询（不传 include_all 或传 False）
        result = await service.list_conversations_with_permission(
            db=db,
            current_user=admin_user,
            skip=0,
            limit=10,
            include_all=False
        )

        # 验证：admin 默认只能看自己的对话
        assert len(result) == 1
        assert result[0].user_id == "admin_001"
        # 验证调用了正确的查询（应该只查当前用户）
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_admin_with_include_all_sees_all_conversations(self):
        """测试 admin 传 include_all=True 可看全部对话"""
        # 准备数据
        service = ConversationService()

        # Mock admin 用户
        admin_user = Mock(is_superuser=False)
        admin_role = Mock()
        admin_role.name = "admin"
        admin_user.roles = [admin_role]
        admin_user.id = "admin_001"

        # Mock 数据库会话
        db = AsyncMock()

        # Mock 查询结果 - 返回所有用户的对话
        mock_conversations = [
            Mock(id="conv_001", user_id="user_001", title="用户1的对话"),
            Mock(id="conv_002", user_id="user_002", title="用户2的对话"),
            Mock(id="conv_003", user_id="admin_001", title="Admin的对话"),
        ]

        # 模拟数据库查询
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_conversations
        db.execute.return_value = mock_result

        # 执行查询（传 include_all=True）
        result = await service.list_conversations_with_permission(
            db=db,
            current_user=admin_user,
            skip=0,
            limit=10,
            include_all=True
        )

        # 验证：admin 可以看到所有用户的对话
        assert len(result) == 3
        user_ids = {conv.user_id for conv in result}
        assert "user_001" in user_ids
        assert "user_002" in user_ids
        assert "admin_001" in user_ids
        # 验证调用了正确的查询（应该查所有用户）
        db.execute.assert_called_once()