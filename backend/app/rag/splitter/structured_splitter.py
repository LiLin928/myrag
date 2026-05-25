"""结构化分块器

适用于长文档+有章节结构，按章节/段落层级分块
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import re


@dataclass
class StructuredChunk:
    """结构化分块"""
    chunk_index: int
    content: str
    content_length: int
    chunk_type: str = "paragraph"  # header/paragraph/table/footer
    section_title: Optional[str] = None
    section_level: int = 1
    parent_section: Optional[str] = None
    page_number: int = 1
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class StructuredSplitter:
    """结构化分块器"""

    # 章节标题正则模式
    SECTION_PATTERNS = [
        r'^第[一二三四五六七八九十]+[章节部分]',       # 中文章节
        r'^第\d+[章节部分]',                           # 数字章节
        r'^[一二三四五六七八九十]+[、.．]',            # 中文序号
        r'^\d+[、.．]\s*',                              # 数字序号
        r'^\d+\.\d+\s*',                                # 多级序号
        r'^#\s+',                                       # Markdown 标题
        r'^##\s+',                                      # Markdown 二级标题
    ]

    def __init__(self, max_chunk_size: int = 1500):
        """
        Args:
            max_chunk_size: 最大分块大小
        """
        self.max_chunk_size = max_chunk_size

    def split(self, parsed_data: Dict) -> List[StructuredChunk]:
        """按结构化数据分块

        Args:
            parsed_data: 解析输出数据，包含 sections 列表

        Returns:
            分块列表
        """
        sections = parsed_data.get("sections", [])
        tables = parsed_data.get("tables", [])
        text = parsed_data.get("text", "")

        chunks = []

        # 如果有结构化章节信息
        if sections:
            chunks = self._split_by_sections(sections)
        else:
            # 从文本提取结构
            chunks = self._extract_structure(text)

        # 处理表格
        for table in tables:
            table_chunk = self._create_table_chunk(table, len(chunks))
            chunks.append(table_chunk)

        return chunks

    def _split_by_sections(self, sections: List[Dict]) -> List[StructuredChunk]:
        """按章节分割

        Args:
            sections: 章节列表 [{title, level, paragraphs}]

        Returns:
            分块列表
        """
        chunks = []
        chunk_index = 0

        for section in sections:
            title = section.get("title")
            level = section.get("level", 1)
            paragraphs = section.get("paragraphs", [])

            # 章节标题作为独立分块
            if title:
                chunks.append(StructuredChunk(
                    chunk_index=chunk_index,
                    content=title,
                    content_length=len(title),
                    chunk_type="header",
                    section_title=title,
                    section_level=level,
                    metadata={"strategy": "structured"},
                ))
                chunk_index += 1

            # 处理段落
            for para in paragraphs:
                para_text = para.get("text", "")
                para_page = para.get("page_number", 1)

                if not para_text:
                    continue

                # 如果段落过大，分割
                if len(para_text) > self.max_chunk_size:
                    sub_chunks = self._split_large_paragraph(
                        para_text, title, level, chunk_index, para_page
                    )
                    chunks.extend(sub_chunks)
                    chunk_index += len(sub_chunks)
                else:
                    chunks.append(StructuredChunk(
                        chunk_index=chunk_index,
                        content=para_text,
                        content_length=len(para_text),
                        chunk_type="paragraph",
                        section_title=title,
                        section_level=level,
                        page_number=para_page,
                        metadata={"strategy": "structured"},
                    ))
                    chunk_index += 1

        return chunks

    def _extract_structure(self, text: str) -> List[StructuredChunk]:
        """从文本提取结构

        Args:
            text: 原始文本

        Returns:
            分块列表
        """
        chunks = []
        chunk_index = 0
        lines = text.split('\n')

        current_section = None
        current_level = 1
        current_content = []

        for line in lines:
            line_stripped = line.strip()

            # 检测章节标题
            is_section = False
            for pattern in self.SECTION_PATTERNS:
                if re.match(pattern, line_stripped):
                    is_section = True
                    break

            if is_section:
                # 保存之前的内容
                if current_content:
                    content_text = '\n'.join(current_content)
                    if content_text.strip():
                        chunks.append(StructuredChunk(
                            chunk_index=chunk_index,
                            content=content_text,
                            content_length=len(content_text),
                            chunk_type="paragraph",
                            section_title=current_section,
                            section_level=current_level,
                            metadata={"strategy": "structured", "auto_extracted": True},
                        ))
                        chunk_index += 1

                # 新章节标题
                current_section = line_stripped
                current_level = self._detect_level(line_stripped)
                current_content = []

                # 章节标题作为独立分块
                chunks.append(StructuredChunk(
                    chunk_index=chunk_index,
                    content=line_stripped,
                    content_length=len(line_stripped),
                    chunk_type="header",
                    section_title=line_stripped,
                    section_level=current_level,
                    metadata={"strategy": "structured"},
                ))
                chunk_index += 1

            else:
                if line_stripped:
                    current_content.append(line)

        # 保存最后的内容
        if current_content:
            content_text = '\n'.join([l for l in current_content if l.strip()])
            if content_text:
                chunks.append(StructuredChunk(
                    chunk_index=chunk_index,
                    content=content_text,
                    content_length=len(content_text),
                    chunk_type="paragraph",
                    section_title=current_section,
                    section_level=current_level,
                    metadata={"strategy": "structured"},
                ))

        return chunks

    def _split_large_paragraph(
        self,
        text: str,
        section_title: str,
        section_level: int,
        start_index: int,
        page_number: int,
    ) -> List[StructuredChunk]:
        """分割大段落

        Args:
            text: 大段落文本
            section_title: 所属章节
            section_level: 章节层级
            start_index: 起始索引
            page_number: 页码

        Returns:
            分块列表
        """
        # 按句子分割
        sentences = self._split_sentences(text)

        chunks = []
        chunk_index = start_index
        current_chunk = []

        for sentence in sentences:
            if sum(len(s) for s in current_chunk) + len(sentence) <= self.max_chunk_size:
                current_chunk.append(sentence)
            else:
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunks.append(StructuredChunk(
                        chunk_index=chunk_index,
                        content=chunk_text,
                        content_length=len(chunk_text),
                        chunk_type="paragraph",
                        section_title=section_title,
                        section_level=section_level,
                        page_number=page_number,
                        metadata={"strategy": "structured", "split": True},
                    ))
                    chunk_index += 1

                current_chunk = [sentence]

        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(StructuredChunk(
                chunk_index=chunk_index,
                content=chunk_text,
                content_length=len(chunk_text),
                chunk_type="paragraph",
                section_title=section_title,
                section_level=section_level,
                page_number=page_number,
                metadata={"strategy": "structured", "split": True},
            ))

        return chunks

    def _create_table_chunk(self, table: Dict, chunk_index: int) -> StructuredChunk:
        """创建表格分块

        Args:
            table: 表格数据
            chunk_index: 分块索引

        Returns:
            表格分块
        """
        # 将表格转换为文本描述
        table_text = self._table_to_text(table)

        return StructuredChunk(
            chunk_index=chunk_index,
            content=table_text,
            content_length=len(table_text),
            chunk_type="table",
            page_number=table.get("page_number", 1),
            metadata={
                "strategy": "structured",
                "table_rows": table.get("rows", 0),
                "table_cols": table.get("cols", 0),
            },
        )

    def _table_to_text(self, table: Dict) -> str:
        """表格转文本

        Args:
            table: 表格数据

        Returns:
            文本描述
        """
        content = table.get("content", [])
        if not content:
            return ""

        lines = []
        for row in content:
            row_text = ' | '.join([str(cell) for cell in row])
            lines.append(row_text)

        return '\n'.join(lines)

    def _detect_level(self, title: str) -> int:
        """检测章节层级

        Args:
            title: 章节标题

        Returns:
            层级（1-4）
        """
        if re.match(r'^第[一二三四五六七八九十]+章', title):
            return 1
        elif re.match(r'^第[一二三四五六七八九十]+节', title):
            return 2
        elif re.match(r'^\d+\.\d+', title):
            return 3
        elif re.match(r'^[一二三四五六七八九十]+、', title):
            return 2
        elif re.match(r'^\d+[、.]', title):
            return 3
        else:
            return 1

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        pattern = r'[。！？\n]+'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def to_dict_list(self, chunks: List[StructuredChunk]) -> List[Dict[str, Any]]:
        """转换为字典列表"""
        return [asdict(chunk) for chunk in chunks]