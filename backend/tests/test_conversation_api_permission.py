"""对话列表 API all_users 参数权限测试"""

import pytest
from unittest.mock import Mock, AsyncMock
from httpx import AsyncClient, ASGITransport


class TestConversationAPIPermission:
    """对话列表 API all_users 参数权限测试"""

    @pytest.mark.asyncio
    async def test_list_conversations_without_all_users_param(self):
        """测试不带 all_users 参数时正常返回用户自己的对话"""
        from app.main import app
        from app.api.dependencies.auth import get_current_user
        from app.db import get_db

        # Mock 普通用户
        normal_user = Mock(is_superuser=False)
        normal_role = Mock()
        normal_role.name = "user"
        normal_user.roles = [normal_role]
        normal_user.id = "user_001"

        # Mock 数据库会话
        db = AsyncMock()
        mock_conversations = [
            Mock(id="conv_001", user_id="user_001", title="用户1的对话",
                 model="gpt-4o-mini", message_count=5, updated_at="2024-01-01"),
            Mock(id="conv_002", user_id="user_001", title="用户1的另一个对话",
                 model="gpt-4o-mini", message_count=3, updated_at="2024-01-02"),
        ]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_conversations
        db.execute.return_value = mock_result

        # 使用 dependency_overrides 覆盖依赖
        app.dependency_overrides[get_current_user] = lambda: normal_user
        app.dependency_overrides[get_db] = lambda: db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get("/api/v1/conversations/")

            # 验证：不带参数正常返回
            assert response.status_code == 200
        finally:
            # 清理依赖覆盖
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_conversations_with_all_users_false(self):
        """测试 all_users=False 时正常返回用户自己的对话"""
        from app.main import app
        from app.api.dependencies.auth import get_current_user
        from app.db import get_db

        # Mock 普通用户
        normal_user = Mock(is_superuser=False)
        normal_role = Mock()
        normal_role.name = "user"
        normal_user.roles = [normal_role]
        normal_user.id = "user_001"

        # Mock 数据库会话
        db = AsyncMock()
        mock_conversations = [
            Mock(id="conv_001", user_id="user_001", title="用户1的对话",
                 model="gpt-4o-mini", message_count=5, updated_at="2024-01-01"),
        ]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_conversations
        db.execute.return_value = mock_result

        app.dependency_overrides[get_current_user] = lambda: normal_user
        app.dependency_overrides[get_db] = lambda: db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get("/api/v1/conversations/?all_users=false")

            # 验证：all_users=false 正常返回
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_normal_user_cannot_use_all_users_true(self):
        """测试普通用户使用 all_users=True 返回 403 错误"""
        from app.main import app
        from app.api.dependencies.auth import get_current_user
        from app.db import get_db

        # Mock 普通用户
        normal_user = Mock(is_superuser=False)
        normal_role = Mock()
        normal_role.name = "user"
        normal_user.roles = [normal_role]
        normal_user.id = "user_001"

        # Mock 数据库会话
        db = AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: normal_user
        app.dependency_overrides[get_db] = lambda: db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get("/api/v1/conversations/?all_users=true")

            # 验证：普通用户不能使用 all_users=true，返回 403
            assert response.status_code == 403
            detail = response.json().get("detail", "")
            assert "权限" in detail or "all_users" in detail.lower() or "管理员" in detail
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_admin_can_use_all_users_true(self):
        """测试 admin 用户可以使用 all_users=True 查看所有对话"""
        from app.main import app
        from app.api.dependencies.auth import get_current_user
        from app.db import get_db

        # Mock admin 用户
        admin_user = Mock(is_superuser=False)
        admin_role = Mock()
        admin_role.name = "admin"
        admin_user.roles = [admin_role]
        admin_user.id = "admin_001"

        # Mock 数据库会话
        db = AsyncMock()
        mock_conversations = [
            Mock(id="conv_001", user_id="user_001", title="用户1的对话",
                 model="gpt-4o-mini", message_count=5, updated_at="2024-01-01"),
            Mock(id="conv_002", user_id="user_002", title="用户2的对话",
                 model="gpt-4o-mini", message_count=3, updated_at="2024-01-02"),
            Mock(id="conv_003", user_id="admin_001", title="Admin的对话",
                 model="gpt-4o-mini", message_count=10, updated_at="2024-01-03"),
        ]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_conversations
        db.execute.return_value = mock_result

        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_db] = lambda: db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get("/api/v1/conversations/?all_users=true")

            # 验证：admin 可以使用 all_users=true
            assert response.status_code == 200
            # 验证返回数据包含 user_id
            data = response.json()
            assert isinstance(data, list)
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_superuser_can_use_all_users_true(self):
        """测试 superuser 可以使用 all_users=True 查看所有对话"""
        from app.main import app
        from app.api.dependencies.auth import get_current_user
        from app.db import get_db

        # Mock superuser
        superuser = Mock(is_superuser=True)
        superuser.roles = []
        superuser.id = "super_001"

        # Mock 数据库会话
        db = AsyncMock()
        mock_conversations = [
            Mock(id="conv_001", user_id="user_001", title="用户1的对话",
                 model="gpt-4o-mini", message_count=5, updated_at="2024-01-01"),
        ]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_conversations
        db.execute.return_value = mock_result

        app.dependency_overrides[get_current_user] = lambda: superuser
        app.dependency_overrides[get_db] = lambda: db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get("/api/v1/conversations/?all_users=true")

            # 验证：superuser 可以使用 all_users=true
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_all_users_response_contains_user_id(self):
        """测试 admin 使用 all_users=True 时返回数据包含 user_id"""
        from app.main import app
        from app.api.dependencies.auth import get_current_user
        from app.db import get_db

        # Mock admin 用户
        admin_user = Mock(is_superuser=False)
        admin_role = Mock()
        admin_role.name = "admin"
        admin_user.roles = [admin_role]
        admin_user.id = "admin_001"

        # Mock 数据库会话
        db = AsyncMock()
        mock_conversations = [
            Mock(id="conv_001", user_id="user_001", title="用户1的对话",
                 model="gpt-4o-mini", message_count=5, updated_at="2024-01-01"),
            Mock(id="conv_002", user_id="admin_001", title="Admin的对话",
                 model="gpt-4o-mini", message_count=10, updated_at="2024-01-03"),
        ]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_conversations
        db.execute.return_value = mock_result

        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_db] = lambda: db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get("/api/v1/conversations/?all_users=true")

            # 验证返回数据包含 user_id
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            # 验证每个对话项包含 user_id
            for conv in data:
                assert "user_id" in conv, "all_users=true 时返回数据应包含 user_id"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_normal_view_without_all_users(self):
        """测试普通查询（不带 all_users）正常工作"""
        from app.main import app
        from app.api.dependencies.auth import get_current_user
        from app.db import get_db

        # Mock 普通用户
        normal_user = Mock(is_superuser=False)
        normal_role = Mock()
        normal_role.name = "user"
        normal_user.roles = [normal_role]
        normal_user.id = "user_001"

        # Mock 数据库会话
        db = AsyncMock()
        mock_conversations = [
            Mock(id="conv_001", user_id="user_001", title="用户1的对话",
                 model="gpt-4o-mini", message_count=5, updated_at="2024-01-01"),
        ]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_conversations
        db.execute.return_value = mock_result

        app.dependency_overrides[get_current_user] = lambda: normal_user
        app.dependency_overrides[get_db] = lambda: db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get("/api/v1/conversations/")

            # 验证正常返回
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
        finally:
            app.dependency_overrides.clear()