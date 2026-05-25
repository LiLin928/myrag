import pytest
from app.rag.extractor.factory import ExtractorFactory
from app.rag.extractor.multimodal_extractor import MultimodalExtractor


class TestExtractorFactoryMultimodal:
    """提取器工厂多模态测试"""

    def test_multimodal_registered(self):
        """测试多模态提取器已注册"""
        assert ".pdf" in ExtractorFactory.get_supported_extensions()
        assert ".png" in ExtractorFactory.get_supported_extensions()

    def test_get_multimodal_extractor_for_pdf(self):
        """测试 PDF 获取多模态提取器"""
        extractor = ExtractorFactory.get_extractor("test.pdf")

        # 应返回优先级最高的 MultimodalExtractor
        assert isinstance(extractor, MultimodalExtractor)

    def test_get_multimodal_extractor_for_image(self):
        """测试图片获取多模态提取器"""
        extractor = ExtractorFactory.get_extractor("test.png")

        assert isinstance(extractor, MultimodalExtractor)

    def test_priority_order(self):
        """测试优先级顺序"""
        # PDF 应使用 MultimodalExtractor（优先级 10）
        # 而不是 MineruExtractor（优先级 3）
        extractor = ExtractorFactory.get_extractor("document.pdf")

        assert extractor.__class__.__name__ == "MultimodalExtractor"