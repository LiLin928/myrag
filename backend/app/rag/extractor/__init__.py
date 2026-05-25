"""文档解析器模块"""

from app.rag.extractor.base_extractor import BaseExtractor, ContentBlock
from app.rag.extractor.text_extractor import TextExtractor
# from app.rag.extractor.mineru_extractor import MineruExtractor  # 暂时注释：MinerU 解析
from app.rag.extractor.unstructured_extractor import UnstructuredExtractor
from app.rag.extractor.multimodal_extractor import MultimodalExtractor
from app.rag.extractor.factory import ExtractorFactory

__all__ = [
    "BaseExtractor",
    "ContentBlock",
    "TextExtractor",
    # "MineruExtractor",  # 暂时注释：MinerU 解析
    "UnstructuredExtractor",
    "MultimodalExtractor",
    "ExtractorFactory",
]