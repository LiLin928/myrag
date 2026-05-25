"""语义分块器

适用于中长文档，按语义边界分块，保留内容连贯性
"""

from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import re


@dataclass
class SemanticChunk:
    """语义分块"""
    chunk_index: int
    content: str
    content_length: int
    page_number: int = 1
    semantic_type: str = "body"  # header/body/conclusion
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SemanticSplitter:
    """语义分块器"""

    # 语义边界关键词
    SEMANTIC_MARKERS = {
        "header": [
            "摘要", "abstract", "引言", "introduction",
            "背景", "background", "概述", "overview",
        ],
        "section_start": [
            "第", "一、", "二、", "三、", "四、", "五、",
            "1.", "2.", "3.", "4.", "5.",
            "第一章", "第二章", "第三章",
        ],
        "conclusion": [
            "结论", "conclusion", "总结", "summary",
            "结束语", "ending", "致谢", "acknowledgment",
        ],
    }

    def __init__(
        self,
        target_chunk_size: int = 800,
        min_chunk_size: int = 200,
        max_chunk_size: int = 1500,
    ):
        """
        Args:
            target_chunk_size: 目标分块大小
            min_chunk_size: 最小分块大小
            max_chunk_size: 最大分块大小
        """
        self.target_chunk_size = target_chunk_size
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

    def split(self, text: str, page_number: int = 1) -> List[SemanticChunk]:
        """按语义边界分块

        Args:
            text: 文本内容
            page_number: 页码

        Returns:
            分块列表
        """
        if not text:
            return []

        # 检测语义边界
        boundaries = self._detect_semantic_boundaries(text)

        # 按边界分割
        chunks = self._split_by_boundaries(text, boundaries, page_number)

        return chunks

    def _detect_semantic_boundaries(self, text: str) -> List[int]:
        """检测语义边界位置

        Args:
            text: 文本内容

        Returns:
            边界位置列表（字符索引）
        """
        boundaries = []

        # 按行检测
        lines = text.split('\n')

        current_pos = 0
        for line in lines:
            line_len = len(line) + 1  # +1 for newline

            # 检测章节开头
            for marker in self.SEMANTIC_MARKERS["section_start"]:
                if line.strip().startswith(marker):
                    boundaries.append(current_pos)
                    break

            # 检测结论部分
            for marker in self.SEMANTIC_MARKERS["conclusion"]:
                if marker in line.lower():
                    boundaries.append(current_pos)
                    break

            current_pos += line_len

        return sorted(set(boundaries))

    def _split_by_boundaries(
        self,
        text: str,
        boundaries: List[int],
        page_number: int,
    ) -> List[SemanticChunk]:
        """按边界分割文本

        Args:
            text: 文本
            boundaries: 边界位置
            page_number: 页码

        Returns:
            分块列表
        """
        chunks = []
        chunk_index = 0

        # 如果没有边界，按固定大小分割
        if not boundaries:
            return self._split_no_boundary(text, page_number)

        # 添加起始和结束位置
        all_boundaries = [0] + boundaries + [len(text)]

        for i in range(len(all_boundaries) - 1):
            start = all_boundaries[i]
            end = all_boundaries[i + 1]

            segment_text = text[start:end].strip()

            if not segment_text:
                continue

            # 如果段落过大，进一步分割
            if len(segment_text) > self.max_chunk_size:
                sub_chunks = self._split_large_segment(
                    segment_text, chunk_index, page_number
                )
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
            else:
                semantic_type = self._detect_semantic_type(segment_text)

                chunks.append(SemanticChunk(
                    chunk_index=chunk_index,
                    content=segment_text,
                    content_length=len(segment_text),
                    page_number=page_number,
                    semantic_type=semantic_type,
                    metadata={"strategy": "semantic", "boundary_detected": True},
                ))
                chunk_index += 1

        return chunks

    def _split_no_boundary(self, text: str, page_number: int) -> List[SemanticChunk]:
        """无边界时的分割策略

        Args:
            text: 文本
            page_number: 页码

        Returns:
            分块列表
        """
        # 按段落分割
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        chunks = []
        chunk_index = 0
        current_content = []

        for para in paragraphs:
            if sum(len(p) for p in current_content) + len(para) <= self.target_chunk_size:
                current_content.append(para)
            else:
                if current_content:
                    chunk_text = '\n\n'.join(current_content)
                    chunks.append(SemanticChunk(
                        chunk_index=chunk_index,
                        content=chunk_text,
                        content_length=len(chunk_text),
                        page_number=page_number,
                        semantic_type="body",
                        metadata={"strategy": "semantic"},
                    ))
                    chunk_index += 1

                current_content = [para]

        if current_content:
            chunk_text = '\n\n'.join(current_content)
            chunks.append(SemanticChunk(
                chunk_index=chunk_index,
                content=chunk_text,
                content_length=len(chunk_text),
                page_number=page_number,
                semantic_type="body",
                metadata={"strategy": "semantic"},
            ))

        return chunks

    def _split_large_segment(
        self,
        text: str,
        start_index: int,
        page_number: int,
    ) -> List[SemanticChunk]:
        """分割大段落

        Args:
            text: 大段落文本
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
        current_length = 0

        for sentence in sentences:
            if current_length + len(sentence) <= self.target_chunk_size:
                current_chunk.append(sentence)
                current_length += len(sentence)
            else:
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunks.append(SemanticChunk(
                        chunk_index=chunk_index,
                        content=chunk_text,
                        content_length=len(chunk_text),
                        page_number=page_number,
                        semantic_type="body",
                        metadata={"strategy": "semantic", "sub_split": True},
                    ))
                    chunk_index += 1

                current_chunk = [sentence]
                current_length = len(sentence)

        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(SemanticChunk(
                chunk_index=chunk_index,
                content=chunk_text,
                content_length=len(chunk_text),
                page_number=page_number,
                semantic_type="body",
                metadata={"strategy": "semantic", "sub_split": True},
            ))

        return chunks

    def _detect_semantic_type(self, text: str) -> str:
        """检测语义类型

        Args:
            text: 文本内容

        Returns:
            类型：header/body/conclusion
        """
        text_lower = text.lower()

        for marker in self.SEMANTIC_MARKERS["header"]:
            if marker in text_lower:
                return "header"

        for marker in self.SEMANTIC_MARKERS["conclusion"]:
            if marker in text_lower:
                return "conclusion"

        return "body"

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        pattern = r'[。！？\n\.]+'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def to_dict_list(self, chunks: List[SemanticChunk]) -> List[Dict[str, Any]]:
        """转换为字典列表"""
        return [asdict(chunk) for chunk in chunks]