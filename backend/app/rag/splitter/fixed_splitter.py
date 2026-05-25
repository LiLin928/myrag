"""固定大小分块器

适用于短文档，按固定字符数分块，保留句子边界
"""

from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import re


@dataclass
class FixedChunk:
    """固定大小分块"""
    chunk_index: int
    content: str
    content_length: int
    page_number: int = 1
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class FixedSplitter:
    """固定大小分块器"""

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
        respect_sentence_boundary: bool = True,
    ):
        """
        Args:
            chunk_size: 分块大小（字符数）
            chunk_overlap: 分块重叠（字符数）
            respect_sentence_boundary: 是否保留句子边界
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.respect_sentence_boundary = respect_sentence_boundary

    def split(self, text: str, page_number: int = 1) -> List[FixedChunk]:
        """将文本分割为固定大小分块

        Args:
            text: 文本内容
            page_number: 页码

        Returns:
            分块列表
        """
        if not text:
            return []

        chunks = []

        if self.respect_sentence_boundary:
            # 按句子分割
            sentences = self._split_sentences(text)
            chunks = self._chunk_by_sentences(sentences, page_number)
        else:
            # 直接按字符分割
            chunks = self._chunk_by_chars(text, page_number)

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子

        Args:
            text: 文本内容

        Returns:
            句子列表
        """
        # 中文句子分割模式
        patterns = [
            r'[。！？\n]',           # 中文句号、感叹号、问号、换行
            r'\.\s+',               # 英文句号+空格
            r'[;；]',               # 分号
        ]

        # 合并模式
        combined_pattern = '|'.join(patterns)

        # 分割并保留分隔符
        sentences = re.split(f'({combined_pattern})', text)

        # 合并分隔符
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else '')
            if sentence.strip():
                result.append(sentence.strip())

        # 处理最后一部分
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            result.append(sentences[-1].strip())

        return result if result else [text]

    def _chunk_by_sentences(self, sentences: List[str], page_number: int) -> List[FixedChunk]:
        """按句子构建分块

        Args:
            sentences: 句子列表
            page_number: 页码

        Returns:
            分块列表
        """
        chunks = []
        chunk_index = 0
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            # 如果单句超过目标大小，单独成块
            if sentence_len > self.chunk_size:
                if current_chunk:
                    chunks.append(FixedChunk(
                        chunk_index=chunk_index,
                        content=' '.join(current_chunk),
                        content_length=current_length,
                        page_number=page_number,
                        metadata={"strategy": "fixed", "sentence_count": len(current_chunk)},
                    ))
                    chunk_index += 1
                    current_chunk = []
                    current_length = 0

                # 大句子单独成块
                chunks.append(FixedChunk(
                    chunk_index=chunk_index,
                    content=sentence,
                    content_length=sentence_len,
                    page_number=page_number,
                    metadata={"strategy": "fixed", "oversized": True},
                ))
                chunk_index += 1

            # 正常添加到当前分块
            elif current_length + sentence_len <= self.chunk_size:
                current_chunk.append(sentence)
                current_length += sentence_len

            # 当前分块已满，创建新块（带重叠）
            else:
                if current_chunk:
                    chunks.append(FixedChunk(
                        chunk_index=chunk_index,
                        content=' '.join(current_chunk),
                        content_length=current_length,
                        page_number=page_number,
                        metadata={"strategy": "fixed", "sentence_count": len(current_chunk)},
                    ))
                    chunk_index += 1

                # 保留重叠部分
                overlap_sentences = self._get_overlap_sentences(current_chunk)
                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s) for s in current_chunk)

        # 保存最后一个分块
        if current_chunk:
            chunks.append(FixedChunk(
                chunk_index=chunk_index,
                content=' '.join(current_chunk),
                content_length=current_length,
                page_number=page_number,
                metadata={"strategy": "fixed", "sentence_count": len(current_chunk)},
            ))

        return chunks

    def _chunk_by_chars(self, text: str, page_number: int) -> List[FixedChunk]:
        """按字符直接分割

        Args:
            text: 文本内容
            page_number: 页码

        Returns:
            分块列表
        """
        chunks = []
        chunk_index = 0
        start = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]

            chunks.append(FixedChunk(
                chunk_index=chunk_index,
                content=chunk_text,
                content_length=len(chunk_text),
                page_number=page_number,
                metadata={"strategy": "fixed"},
            ))

            chunk_index += 1
            start = end - self.chunk_overlap if end < len(text) else end

        return chunks

    def _get_overlap_sentences(self, sentences: List[str]) -> List[str]:
        """获取重叠部分的句子

        Args:
            sentences: 当前句子列表

        Returns:
            重叠句子
        """
        if not sentences:
            return []

        overlap_length = 0
        overlap_sentences = []

        # 从后向前取句子，直到达到重叠长度
        for sentence in reversed(sentences):
            if overlap_length + len(sentence) <= self.chunk_overlap:
                overlap_sentences.insert(0, sentence)
                overlap_length += len(sentence)
            else:
                break

        return overlap_sentences

    def to_dict_list(self, chunks: List[FixedChunk]) -> List[Dict[str, Any]]:
        """转换为字典列表"""
        return [asdict(chunk) for chunk in chunks]