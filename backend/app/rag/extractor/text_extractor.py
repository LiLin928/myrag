"""纯文本解析器

支持：.txt, .md
"""

from typing import List
from pathlib import Path

from app.rag.extractor.base_extractor import BaseExtractor, ContentBlock


class TextExtractor(BaseExtractor):
    """纯文本解析器"""

    SUPPORTED_EXTENSIONS = [".txt", ".md", ".text", ".markdown"]

    async def extract(self, file_path: str) -> List[ContentBlock]:
        """解析纯文本文件

        Args:
            file_path: 文件路径

        Returns:
            内容块列表
        """
        path = Path(file_path)

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # 简单分块：按段落分割
        paragraphs = content.split("\n\n")

        blocks = []
        for i, para in enumerate(paragraphs):
            if para.strip():
                blocks.append(ContentBlock(
                    type="text",
                    content=para.strip(),
                    page_number=1,  # 纯文本无页码
                    metadata={
                        "paragraph_index": i,
                        "source": path.name,
                    }
                ))

        return blocks

    @classmethod
    def supports_file_type(cls, file_extension: str) -> bool:
        """检查是否支持"""
        return file_extension.lower() in cls.SUPPORTED_EXTENSIONS