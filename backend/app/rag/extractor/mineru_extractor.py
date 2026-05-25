"""MinerU PDF 解析器

使用 MinerU 2.0 解析 PDF 文件：
- 公式识别（LaTeX 输出）
- 表格识别（HTML/Markdown）
- 图片 OCR
- 多栏布局识别
"""

from typing import List, Dict, Any
import json
from pathlib import Path
import tempfile

from app.rag.extractor.base_extractor import BaseExtractor, ContentBlock


class MineruExtractor(BaseExtractor):
    """MinerU PDF 解析器"""

    SUPPORTED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg"]

    async def extract(self, file_path: str) -> List[ContentBlock]:
        """使用 MinerU 解析 PDF

        Args:
            file_path: PDF 文件路径

        Returns:
            内容块列表
        """
        from app.services.multimodal.mineru_client import MinerUClient

        try:
            # 调用 MinerU API
            client = MinerUClient()
            result = await client.parse_pdf(
                file_path,
                output_format="markdown",
                extract_tables=True,
                extract_formulas=True,
            )

            # 转换响应格式
            parsed_result = client.parse_mineru_response(result)

            blocks = []

            # 添加主文本内容
            if parsed_result.get("content"):
                blocks.append(ContentBlock(
                    type="text",
                    content=parsed_result["content"],
                    page_number=1,
                    metadata={
                        "source": file_path,
                        "extractor": "mineru",
                        "pages": parsed_result["metadata"].get("pages", 0),
                    }
                ))

            # 添加表格
            for table in parsed_result.get("tables", []):
                blocks.append(ContentBlock(
                    type="table",
                    content=table.get("html", table.get("markdown", "")),
                    page_number=table.get("page", 1),
                    metadata={"table_id": table.get("id")}
                ))

            # 添加公式
            for formula in parsed_result.get("formulas", []):
                blocks.append(ContentBlock(
                    type="formula",
                    content=formula.get("latex", ""),
                    page_number=formula.get("page", 1),
                    metadata={"formula_id": formula.get("id")}
                ))

            await client.close()
            return blocks

        except Exception as e:
            # MinerU API 失败，返回错误信息
            blocks = [
                ContentBlock(
                    type="text",
                    content=f"PDF 解析失败（MinerU API 错误: {str(e)}）",
                    page_number=1,
                    metadata={"source": file_path, "extractor": "mineru", "error": str(e)}
                )
            ]
            return blocks

    @classmethod
    def supports_file_type(cls, file_extension: str) -> bool:
        """检查是否支持"""
        return file_extension.lower() in cls.SUPPORTED_EXTENSIONS

    def parse_mineru_output(self, output_dir: Path) -> List[ContentBlock]:
        """解析 MinerU 输出结果

        MinerU 输出格式：
        - Markdown 文件：主文本内容
        - JSON 文件：结构化数据（表格、公式）
        - 图片文件：提取的图片

        Args:
            output_dir: MinerU 输出目录

        Returns:
            内容块列表
        """
        blocks = []

        # 读取 Markdown 文件
        md_file = output_dir / "output.md"
        if md_file.exists():
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 简单分块
            sections = content.split("\n## ")
            for i, section in enumerate(sections):
                if section.strip():
                    blocks.append(ContentBlock(
                        type="text",
                        content=section.strip(),
                        page_number=i + 1,
                        metadata={"format": "markdown"}
                    ))

        # 读取 JSON 文件（表格、公式）
        json_file = output_dir / "output.json"
        if json_file.exists():
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for item in data.get("tables", []):
                blocks.append(ContentBlock(
                    type="table",
                    content=item.get("html", ""),
                    page_number=item.get("page", 1),
                    metadata={"table_id": item.get("id")}
                ))

            for item in data.get("formulas", []):
                blocks.append(ContentBlock(
                    type="formula",
                    content=item.get("latex", ""),
                    page_number=item.get("page", 1),
                    metadata={"formula_id": item.get("id")}
                ))

        return blocks