"""安全工具测试"""
import pytest
from datetime import timedelta
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_subject,
    get_token_type,
)


class TestPasswordHash:
    """密码哈希测试"""

    def test_password_hash_creates_hash(self):
        """测试密码哈希生成"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert hashed.startswith("$2b$")

    def test_password_hash_verifies_correct_password(self):
        """测试正确密码验证"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_password_hash_verifies_wrong_password(self):
        """测试错误密码验证"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password("wrongpassword", hashed) is False

    def test_different_passwords_different_hashes(self):
        """测试不同密码生成不同哈希"""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        # bcrypt 每次生成不同的哈希（因为有随机盐）
        assert hash1 != hash2
        # 但都能验证原密码
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestJWTToken:
    """JWT 令牌测试"""

    def test_create_access_token(self):
        """测试创建访问令牌"""
        user_id = "test-user-123"
        token = create_access_token(subject=user_id)
        assert token is not None
        assert isinstance(token, str)

    def test_create_access_token_with_expiry(self):
        """测试带过期时间的访问令牌"""
        user_id = "test-user-123"
        expires = timedelta(hours=1)
        token = create_access_token(subject=user_id, expires_delta=expires)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "access"

    def test_create_access_token_with_extra_data(self):
        """测试带额外数据的访问令牌"""
        user_id = "test-user-123"
        extra = {"role": "admin", "email": "test@example.com"}
        token = create_access_token(subject=user_id, extra_data=extra)
        payload = decode_token(token)
        assert payload is not None
        assert payload["role"] == "admin"
        assert payload["email"] == "test@example.com"

    def test_create_refresh_token(self):
        """测试创建刷新令牌"""
        user_id = "test-user-123"
        token = create_refresh_token(subject=user_id)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"

    def test_decode_valid_token(self):
        """测试解码有效令牌"""
        user_id = "test-user-123"
        token = create_access_token(subject=user_id)
        payload = decode_token(token)
        assert payload is not None
        assert "sub" in payload
        assert "exp" in payload

    def test_decode_invalid_token(self):
        """测试解码无效令牌"""
        invalid_token = "invalid.token.here"
        payload = decode_token(invalid_token)
        assert payload is None

    def test_get_token_subject(self):
        """测试获取令牌主题"""
        user_id = "test-user-123"
        token = create_access_token(subject=user_id)
        subject = get_token_subject(token)
        assert subject == user_id

    def test_get_token_subject_invalid(self):
        """测试获取无效令牌主题"""
        invalid_token = "invalid.token.here"
        subject = get_token_subject(invalid_token)
        assert subject is None

    def test_get_token_type_access(self):
        """测试获取访问令牌类型"""
        token = create_access_token(subject="test-user")
        token_type = get_token_type(token)
        assert token_type == "access"

    def test_get_token_type_refresh(self):
        """测试获取刷新令牌类型"""
        token = create_refresh_token(subject="test-user")
        token_type = get_token_type(token)
        assert token_type == "refresh"
