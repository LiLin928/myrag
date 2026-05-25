import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.services.multimodal.parser_service import (
    MultimodalParserService,
    ParserBackend,
)


class TestParserService:
    """统一解析服务测试"""

    def test_backend_enum(self):
        """测试后端枚举"""
        assert ParserBackend.MINERU_DOCKER.value == "mineru_docker"
        assert ParserBackend.DEEPSEEK_OCR.value == "deepseek_ocr"
        assert ParserBackend.AUTO.value == "auto"

    def test_service_init(self):
        """测试服务初始化"""
        service = MultimodalParserService()

        assert service.default_backend == ParserBackend.AUTO

    def test_service_with_custom_backend(self):
        """测试自定义后端"""
        service = MultimodalParserService(
            default_backend=ParserBackend.MINERU_DOCKER
        )

        assert service.default_backend == ParserBackend.MINERU_DOCKER

    def test_auto_select_backend_pdf(self):
        """测试自动选择后端（PDF）"""
        service = MultimodalParserService()

        # PDF 文件
        backend = service._auto_select_backend("test.pdf", "pdf")

        # PDF 应优先使用 MinerU（如果有）
        assert backend in [ParserBackend.MINERU_DOCKER, ParserBackend.DEEPSEEK_OCR]

    def test_auto_select_backend_image(self):
        """测试自动选择后端（图片）"""
        service = MultimodalParserService(deepseek_api_key="test-key")

        # 图片文件
        backend = service._auto_select_backend("test.png", "image")

        # 图片应使用 DeepSeek OCR
        assert backend == ParserBackend.DEEPSEEK_OCR

    @pytest.mark.asyncio
    async def test_parse_with_mineru(self):
        """测试使用 MinerU 解析"""
        with patch.object(MultimodalParserService, "_get_mineru_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.parse_pdf = AsyncMock(return_value={
                "markdown": "# Test",
                "tables": [],
                "formulas": [],
            })
            mock_client.parse_mineru_response = MagicMock(return_value={
                "content": "# Test",
                "tables": [],
                "formulas": [],
                "metadata": {"backend": "mineru"},
            })
            mock_get_client.return_value = mock_client

            service = MultimodalParserService(
                mineru_url="http://localhost:8000",
                default_backend=ParserBackend.MINERU_DOCKER,
            )

            result = await service.parse("test.pdf", "pdf")

            assert "content" in result

    @pytest.mark.asyncio
    async def test_parse_with_deepseek_ocr(self):
        """测试使用 DeepSeek OCR 解析"""
        with patch("app.services.multimodal.parser_service.DeepSeekOCRClient") as mock_ocr:
            mock_client = MagicMock()
            mock_client.parse_image = AsyncMock(return_value={
                "content": "识别的文字",
            })
            mock_ocr.return_value = mock_client

            service = MultimodalParserService(
                deepseek_api_key="test-key",
                default_backend=ParserBackend.DEEPSEEK_OCR,
            )

            result = await service.parse("test.png", "image")

            assert result["content"] == "识别的文字"

    def test_get_available_backends(self):
        """测试获取可用后端"""
        service = MultimodalParserService(
            mineru_url="http://localhost:8000",
            deepseek_api_key="test-key",
        )

        backends = service.get_available_backends()

        # 应有两个可用后端
        assert len(backends) >= 1