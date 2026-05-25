"""模型测试"""
import pytest
from app.models.user import User, user_roles
from app.models.role import Role, Permission, DEFAULT_ROLES
# 导入相关模型以便 SQLAlchemy 能解析 relationship
from app.models.knowledge_base import KnowledgeBase
from app.workflow.models.workflow import Workflow


class TestPermission:
    """权限枚举测试"""

    def test_permission_values(self):
        """测试权限值格式"""
        assert Permission.PROJECT_CREATE.value == "project:create"
        assert Permission.DOCUMENT_READ.value == "document:read"
        assert Permission.SYSTEM_ADMIN.value == "system:admin"

    def test_permission_count(self):
        """测试权限总数"""
        assert len(Permission) == 19


class TestRole:
    """角色模型测试"""

    def test_role_creation(self):
        """测试角色创建"""
        role = Role(
            name="test_role",
            description="测试角色",
            permissions=[Permission.PROJECT_READ.value, Permission.DOCUMENT_READ.value],
        )
        assert role.name == "test_role"
        assert role.description == "测试角色"
        assert len(role.permissions) == 2

    def test_role_has_permission(self):
        """测试权限检查方法"""
        role = Role(
            name="viewer",
            permissions=[Permission.PROJECT_READ.value, Permission.DOCUMENT_READ.value],
        )
        assert role.has_permission(Permission.PROJECT_READ.value) is True
        assert role.has_permission(Permission.PROJECT_DELETE.value) is False

    def test_role_default_permissions(self):
        """测试默认角色权限"""
        assert len(DEFAULT_ROLES) == 3
        assert "admin" in DEFAULT_ROLES
        assert "editor" in DEFAULT_ROLES
        assert "viewer" in DEFAULT_ROLES

    def test_admin_has_all_permissions(self):
        """测试管理员拥有所有权限"""
        admin_perms = DEFAULT_ROLES["admin"]["permissions"]
        assert len(admin_perms) == 19
        for perm in Permission:
            assert perm.value in admin_perms

    def test_viewer_has_limited_permissions(self):
        """测试查看者权限有限"""
        viewer_perms = DEFAULT_ROLES["viewer"]["permissions"]
        assert len(viewer_perms) == 4
        assert Permission.PROJECT_READ.value in viewer_perms
        assert Permission.DOCUMENT_READ.value in viewer_perms
        assert Permission.WORKFLOW_EXECUTE.value in viewer_perms
        assert Permission.SKILL_EXECUTE.value in viewer_perms


class TestUser:
    """用户模型测试"""

    def test_user_creation(self):
        """测试用户创建"""
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            full_name="Test User",
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        # Note: SQLAlchemy Column defaults apply at DB level, not Python object creation

    def test_user_default_values(self):
        """测试用户默认值"""
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
        )
        assert user.full_name is None
        # Note: SQLAlchemy Column defaults (is_active, is_superuser) apply at DB level

    def test_user_repr(self):
        """测试用户字符串表示"""
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
        )
        assert repr(user) == "<User testuser>"


class TestUserRoleAssociation:
    """用户角色关联测试"""

    def test_association_table_structure(self):
        """测试关联表结构"""
        columns = [col.name for col in user_roles.columns]
        assert "user_id" in columns
        assert "role_id" in columns
