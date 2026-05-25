import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import base64

from app.services.multimodal.deepseek_ocr_client import DeepSeekOCRClient


class TestDeepSeekOCRClient:
    """DeepSeek-OCR 客户端测试"""

    def test_client_init(self):
        """测试客户端初始化"""
        client = DeepSeekOCRClient(api_key="test-key")

        assert client.api_key == "test-key"
        assert client.model_name == "deepseek-ocr"

    def test_encode_image(self):
        """测试图片编码"""
        client = DeepSeekOCRClient(api_key="test-key")

        # 使用临时图片文件
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # 创建最小 PNG 文件
            f.write(b"\x89PNG\r\n\x1a\n" + b"x" * 100)
            temp_path = f.name

        encoded = client._encode_image(temp_path)

        assert isinstance(encoded, str)
        # 验证 base64 格式
        try:
            base64.b64decode(encoded)
            is_valid = True
        except Exception:
            is_valid = False
        assert is_valid

    def test_build_ocr_prompt(self):
        """测试 OCR prompt 构建"""
        client = DeepSeekOCRClient(api_key="test-key")

        prompt = client._build_ocr_prompt(task="full_parse")

        assert "OCR" in prompt or "识别" in prompt

    @pytest.mark.asyncio
    async def test_parse_image_mock(self):
        """测试图片解析（mock）"""
        with patch.object(DeepSeekOCRClient, "_get_model") as mock_get_model:
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.content = "识别结果：这是测试文本"
            mock_model.ainvoke = AsyncMock(return_value=mock_response)
            mock_get_model.return_value = mock_model

            client = DeepSeekOCRClient(api_key="test-key")

            # 创建临时图片
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(b"\xff\xd8\xff\xe0" + b"x" * 100)
                temp_path = f.name

            result = await client.parse_image(temp_path)

            assert "content" in result

    def test_supported_formats(self):
        """测试支持的格式"""
        from app.services.multimodal.deepseek_ocr_client import SUPPORTED_IMAGE_FORMATS

        assert ".png" in SUPPORTED_IMAGE_FORMATS
        assert ".jpg" in SUPPORTED_IMAGE_FORMATS
        assert ".jpeg" in SUPPORTED_IMAGE_FORMATS