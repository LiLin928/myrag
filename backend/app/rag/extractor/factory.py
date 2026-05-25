"""解析器工厂

根据文件类型选择合适的解析器
"""

from typing import Optional
from pathlib import Path

from app.rag.extractor.base_extractor import BaseExtractor
from app.rag.extractor.text_extractor import TextExtractor
# from app.rag.extractor.mineru_extractor import MineruExtractor  # 暂时注释：MinerU 解析
from app.rag.extractor.unstructured_extractor import UnstructuredExtractor
from app.rag.extractor.multimodal_extractor import MultimodalExtractor


class ExtractorFactory:
    """解析器工厂"""

    # 解析器注册表（优先级：后注册的优先）
    _extractors: dict = {}

    @classmethod
    def register(cls, extractor_class: type, priority: int = 0):
        """注册解析器

        Args:
            extractor_class: 解析器类
            priority: 优先级（数字越大优先级越高）
        """
        for ext in extractor_class.SUPPORTED_EXTENSIONS:
            # 存储为元组 (extractor_class, priority)
            existing = cls._extractors.get(ext.lower())
            if existing:
                # 已存在，比较优先级
                if priority > existing[1]:
                    cls._extractors[ext.lower()] = (extractor_class, priority)
            else:
                cls._extractors[ext.lower()] = (extractor_class, priority)

    @classmethod
    def get_extractor(cls, file_path: str) -> Optional[BaseExtractor]:
        """获取解析器

        Args:
            file_path: 文件路径

        Returns:
            解析器实例，不支持则返回 None
        """
        extension = Path(file_path).suffix.lower()

        entry = cls._extractors.get(extension)
        if entry:
            extractor_class = entry[0]
            return extractor_class()

        return None

    @classmethod
    def supports(cls, file_path: str) -> bool:
        """检查是否支持该文件类型"""
        extension = Path(file_path).suffix.lower()
        return extension in cls._extractors

    @classmethod
    def get_supported_extensions(cls) -> list:
        """获取所有支持的扩展名"""
        return list(cls._extractors.keys())


# 注册所有解析器
# 注意：多模态提取器优先级最高
ExtractorFactory.register(TextExtractor, priority=1)
ExtractorFactory.register(UnstructuredExtractor, priority=2)
# ExtractorFactory.register(MineruExtractor, priority=3)  # 暂时注释：MinerU 解析
ExtractorFactory.register(MultimodalExtractor, priority=10)  # 最高优先级