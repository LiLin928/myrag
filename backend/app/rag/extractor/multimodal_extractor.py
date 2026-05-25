"""多模态文档提取器

整合 MinerU 和 DeepSeek-OCR 进行 PDF/图片文档解析。
"""

from typing import List, Dict, Any, Optional
from pathlib import Path

from app.rag.extractor.base_extractor import BaseExtractor, ContentBlock
from app.services.multimodal.parser_service import (
    parser_service,
    ParserBackend,
)


class MultimodalExtractor(BaseExtractor):
    """多模态文档提取器

    支持 PDF 和图片文件的高质量解析。

    Features:
    - PDF 公式识别（LaTeX）
    - PDF 表格识别（Markdown/HTML）
    - 图片 OCR
    - 多栏布局识别
    """

    SUPPORTED_EXTENSIONS = [
        ".pdf",
        ".png", ".jpg", ".jpeg",
        ".gif", ".bmp", ".webp",
    ]

    def __init__(
        self,
        backend: Optional[ParserBackend] = None,
    ):
        """初始化提取器

        Args:
            backend: 指定解析后端，None 则自动选择
        """
        self.backend = backend
        self.parser_service = parser_service

    async def extract(self, file_path: str) -> List[ContentBlock]:
        """提取文档内容

        Args:
            file_path: 文件路径

        Returns:
            内容块列表
        """
        # 确定文件类型
        ext = Path(file_path).suffix.lower()
        file_type = "pdf" if ext == ".pdf" else "image"

        # 调用解析服务
        try:
            result = await self.parser_service.parse(
                file_path=file_path,
                file_type=file_type,
                backend=self.backend,
            )
        except Exception as e:
            # 解析失败，返回错误块
            return [
                ContentBlock(
                    type="text",
                    content=f"解析失败: {str(e)}",
                    page_number=1,
                    metadata={"error": str(e)},
                )
            ]

        # 转换为内容块
        blocks = self._convert_to_blocks(result, file_path)

        return blocks

    def _convert_to_blocks(
        self,
        result: Dict[str, Any],
        file_path: str,
    ) -> List[ContentBlock]:
        """将解析结果转换为内容块

        Args:
            result: 解析结果
            file_path: 文件路径

        Returns:
            内容块列表
        """
        blocks = []

        # 主文本内容分块
        content = result.get("content", "")
        if content:
            text_blocks = self._split_content_to_blocks(content, file_path)
            blocks.extend(text_blocks)

        # 表格
        for i, table in enumerate(result.get("tables", [])):
            blocks.append(ContentBlock(
                type="table",
                content=table.get("content", table.get("html", "")),
                page_number=table.get("page", 1),
                metadata={
                    "table_id": i,
                    "format": "markdown",
                },
            ))

        # 公式
        for i, formula in enumerate(result.get("formulas", [])):
            blocks.append(ContentBlock(
                type="formula",
                content=formula.get("latex", formula.get("content", "")),
                page_number=formula.get("page", 1),
                metadata={
                    "formula_id": i,
                    "format": "latex",
                },
            ))

        # 添加元数据块
        metadata = result.get("metadata", {})
        if metadata:
            blocks.append(ContentBlock(
                type="metadata",
                content=str(metadata),
                page_number=0,
                metadata=metadata,
            ))

        return blocks

    def _split_content_to_blocks(
        self,
        content: str,
        file_path: str,
    ) -> List[ContentBlock]:
        """将文本内容分割为块

        按段落/标题分块，保持语义完整性。

        Args:
            content: 文本内容
            file_path: 文件路径

        Returns:
            内容块列表
        """
        blocks = []

        # 按段落分割（空行分隔）
        paragraphs = content.split("\n\n")

        page_number = 1
        for para in paragraphs:
            if not para.strip():
                continue

            # 判断类型
            para_type = "text"
            if para.startswith("#"):
                para_type = "heading"
            elif para.startswith("|"):
                para_type = "table"

            blocks.append(ContentBlock(
                type=para_type,
                content=para.strip(),
                page_number=page_number,
                metadata={
                    "source": file_path,
                    "char_count": len(para),
                },
            ))

        return blocks

    @classmethod
    def supports_file_type(cls, file_extension: str) -> bool:
        """检查是否支持"""
        return file_extension.lower() in cls.SUPPORTED_EXTENSIONS