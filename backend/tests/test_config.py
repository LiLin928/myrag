# tests/test_config.py

from app.config import get_settings


def test_deepseek_api_key_configured():
    """测试 DeepSeek API 配置"""
    settings = get_settings()

    assert hasattr(settings, "DEEPSEEK_API_KEY")
    assert hasattr(settings, "DEEPSEEK_API_BASE")
    assert hasattr(settings, "DEEPSEEK_CHAT_MODEL")
    assert hasattr(settings, "DEEPSEEK_REASONER_MODEL")


def test_default_deepseek_models():
    """测试默认模型配置"""
    settings = get_settings()

    assert settings.DEEPSEEK_CHAT_MODEL == "deepseek-chat"
    assert settings.DEEPSEEK_REASONER_MODEL == "deepseek-reasoner"


class TestMultimodalConfig:
    """多模态配置测试"""

    def test_mineru_config(self):
        """测试 MinerU 配置"""
        from app.config import get_settings

        settings = get_settings()

        assert hasattr(settings, "MINERU_API_URL")
        assert hasattr(settings, "MINERU_TIMEOUT")

    def test_ocr_config(self):
        """测试 OCR 配置"""
        from app.config import get_settings

        settings = get_settings()

        assert hasattr(settings, "DEEPSEEK_OCR_MODEL")

    def test_default_config_values(self):
        """测试默认配置值"""
        from app.config import get_settings

        settings = get_settings()

        assert settings.MINERU_API_URL == "http://localhost:8000"
        assert settings.MINERU_TIMEOUT == 300
        assert settings.DEEPSEEK_OCR_MODEL == "deepseek-ocr"