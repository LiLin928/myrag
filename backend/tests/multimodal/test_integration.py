import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import tempfile

from app.services.multimodal.parser_service import MultimodalParserService, ParserBackend
from app.rag.extractor.multimodal_extractor import MultimodalExtractor
from app.rag.extractor.factory import ExtractorFactory


class TestMultimodalIntegration:
    """多模态集成测试"""

    @pytest.mark.asyncio
    async def test_full_parse_pipeline_pdf(self):
        """测试完整 PDF 解析流程"""
        with patch.object(MultimodalParserService, "_get_mineru_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.parse_pdf = AsyncMock(return_value={
                "markdown": "# Document\n\nContent paragraph.",
                "tables": [],
                "formulas": [],
            })
            mock_client.parse_mineru_response = MagicMock(return_value={
                "content": "# Document\n\nContent paragraph.",
                "tables": [],
                "formulas": [],
                "metadata": {"backend": "mineru"},
            })
            mock_get_client.return_value = mock_client

            # 创建临时 PDF
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(b"%PDF-1.4 test")
                temp_path = f.name

            # 使用工厂获取提取器
            extractor = ExtractorFactory.get_extractor(temp_path)
            blocks = await extractor.extract(temp_path)

            assert len(blocks) > 0

    @pytest.mark.asyncio
    async def test_full_parse_pipeline_image(self):
        """测试完整图片解析流程"""
        with patch.object(MultimodalParserService, "_get_deepseek_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.parse_image = AsyncMock(return_value={
                "content": "识别的文字",
            })
            mock_get_client.return_value = mock_client

            # 创建临时图片
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                f.write(b"\x89PNG test")
                temp_path = f.name

            extractor = ExtractorFactory.get_extractor(temp_path)
            blocks = await extractor.extract(temp_path)

            assert len(blocks) > 0

    @pytest.mark.asyncio
    async def test_backend_health_check(self):
        """测试后端健康检查"""
        service = MultimodalParserService(
            mineru_url="http://localhost:8000",
            deepseek_api_key="test-key",
        )

        with patch.object(service, "_get_mineru_client") as mock_mineru_get:
            mock_mineru = MagicMock()
            mock_mineru.health_check = AsyncMock(return_value={"status": "healthy"})
            mock_mineru_get.return_value = mock_mineru

            status = await service.health_check()

            assert "mineru" in status
            assert "deepseek_ocr" in status

    def test_factory_supports_all_multimodal_formats(self):
        """测试工厂支持所有多模态格式"""
        supported = ExtractorFactory.get_supported_extensions()

        # PDF
        assert ".pdf" in supported

        # 图片格式
        for ext in [".png", ".jpg", ".jpeg"]:
            assert ext in supported