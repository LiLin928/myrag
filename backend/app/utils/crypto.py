"""加密工具模块

用于 API Key 的加密存储和解密读取
"""

from cryptography.fernet import Fernet, InvalidToken
import os
import base64
import hashlib
import logging

logger = logging.getLogger(__name__)

# 从环境变量获取加密密钥，若无则生成临时密钥
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")


def get_fernet_key() -> bytes:
    """获取或生成 Fernet 密钥

    使用 SHA256 从 ENCRYPTION_KEY 派生 32 字节密钥，
    若未设置则生成随机密钥（仅用于开发环境）
    """
    if ENCRYPTION_KEY:
        # Use SHA256 to derive a proper 32-byte key
        key_hash = hashlib.sha256(ENCRYPTION_KEY.encode()).digest()
        return base64.urlsafe_b64encode(key_hash)
    else:
        # 生成随机密钥（仅用于开发环境）
        logger.warning("ENCRYPTION_KEY not set, using generated key. API keys will be unreadable after restart!")
        return Fernet.generate_key()


_fernet = None


def get_fernet() -> Fernet:
    """获取 Fernet 实例"""
    global _fernet
    if _fernet is None:
        _fernet = Fernet(get_fernet_key())
    return _fernet


def encrypt_api_key(api_key: str | None) -> str:
    """加密 API Key

    Args:
        api_key: 原始 API Key

    Returns:
        加密后的字符串
    """
    if not api_key:
        return ""
    fernet = get_fernet()
    encrypted = fernet.encrypt(api_key.encode())
    return encrypted.decode()


def decrypt_api_key(encrypted_key: str | None) -> str:
    """解密 API Key

    Args:
        encrypted_key: 加密后的字符串

    Returns:
        原始 API Key，解密失败时返回空字符串
    """
    if not encrypted_key:
        return ""
    fernet = get_fernet()
    try:
        decrypted = fernet.decrypt(encrypted_key.encode())
        return decrypted.decode()
    except InvalidToken:
        logger.warning("Failed to decrypt API key: invalid token")
        return ""


def mask_api_key(api_key: str | None) -> str:
    """脱敏显示 API Key

    Args:
        api_key: 原始或加密的 API Key

    Returns:
        脱敏后的显示，如 "sk-ab***"
    """
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "***"
    return api_key[:4] + "***"