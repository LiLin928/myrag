"""解析器基类"""

from typing import List, Dict, Any
from abc import ABC, abstractmethod
from pathlib import Path


class ContentBlock(dict):
    """内容块结构

    统一的解析输出格式
    """

    def __init__(
        self,
        type: str,
        content: str,
        page_number: int = 1,
        metadata: Dict[str, Any] = None,
    ):
        super().__init__(
            type=type,
            content=content,
            page_number=page_number,
            metadata=metadata or {},
        )


class BaseExtractor(ABC):
    """解析器基类"""

    SUPPORTED_EXTENSIONS: List[str] = []

    @abstractmethod
    async def extract(self, file_path: str) -> List[ContentBlock]:
        """解析文档

        Args:
            file_path: 文件路径

        Returns:
            内容块列表，每个块包含：
            - type: 内容类型（text/table/formula/image）
            - content: 文本内容
            - page_number: 页码
            - metadata: 元数据
        """
        pass

    @classmethod
    def supports_file_type(cls, file_extension: str) -> bool:
        """检查是否支持该文件类型

        Args:
            file_extension: 文件扩展名（如 .pdf）

        Returns:
            是否支持
        """
        return file_extension.lower() in cls.SUPPORTED_EXTENSIONS