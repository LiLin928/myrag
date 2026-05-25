import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.rag.extractor.multimodal_extractor import MultimodalExtractor


class TestMultimodalExtractor:
    """多模态提取器测试"""

    def test_extractor_supported_extensions(self):
        """测试支持的扩展名"""
        assert ".pdf" in MultimodalExtractor.SUPPORTED_EXTENSIONS
        assert ".png" in MultimodalExtractor.SUPPORTED_EXTENSIONS
        assert ".jpg" in MultimodalExtractor.SUPPORTED_EXTENSIONS

    def test_extractor_init(self):
        """测试提取器初始化"""
        extractor = MultimodalExtractor()

        assert extractor.parser_service is not None

    @pytest.mark.asyncio
    async def test_extract_pdf(self):
        """测试提取 PDF"""
        with patch("app.rag.extractor.multimodal_extractor.parser_service") as mock_service:
            mock_service.parse = AsyncMock(return_value={
                "content": "# Test Document\n\nThis is test content.",
                "tables": [],
                "formulas": [],
                "metadata": {"backend": "mineru"},
            })

            extractor = MultimodalExtractor()

            # 创建临时 PDF 文件
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(b"%PDF-1.4 test")
                temp_path = f.name

            blocks = await extractor.extract(temp_path)

            assert len(blocks) > 0
            # ContentBlock 继承自 dict，使用字典访问
            assert blocks[0]["type"] == "heading"

    @pytest.mark.asyncio
    async def test_extract_image(self):
        """测试提取图片"""
        with patch("app.rag.extractor.multimodal_extractor.parser_service") as mock_service:
            mock_service.parse = AsyncMock(return_value={
                "content": "识别的文字内容",
                "tables": [],
                "formulas": [],
            })

            extractor = MultimodalExtractor()

            # 创建临时图片文件
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                f.write(b"\x89PNG\r\n\x1a\n" + b"x" * 100)
                temp_path = f.name

            blocks = await extractor.extract(temp_path)

            assert len(blocks) > 0

    def test_split_content_to_blocks(self):
        """测试内容分块"""
        extractor = MultimodalExtractor()

        content = "# Title\n\nParagraph 1\n\nParagraph 2"
        blocks = extractor._split_content_to_blocks(content, file_path="test.pdf")

        assert len(blocks) > 0
        # 应按段落分块
        # ContentBlock 继承自 dict，使用字典访问
        assert blocks[0]["type"] == "heading"