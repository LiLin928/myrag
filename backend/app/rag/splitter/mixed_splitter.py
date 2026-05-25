"""混合分块器

自动选择最佳分块策略：
- 结构化分块：长文档+有章节结构
- 语义分块：中长文档
- 固定大小分块：短文档
"""

from typing import List, Dict, Any

from app.rag.splitter.structured_splitter import StructuredSplitter, StructuredChunk
from app.rag.splitter.semantic_splitter import SemanticSplitter, SemanticChunk
from app.rag.splitter.fixed_splitter import FixedSplitter, FixedChunk


class MixedSplitter:
    """混合分块器"""

    # 策略选择阈值
    LONG_DOC_THRESHOLD = 5000      # 长文档阈值（字符数）
    MEDIUM_DOC_THRESHOLD = 2000    # 中等文档阈值
    STRUCTURE_HINT_THRESHOLD = 3   # 结构提示阈值（章节数量）

    def __init__(
        self,
        default_strategy: str = "auto",
        chunk_size: int = 800,
        chunk_overlap: int = 100,
    ):
        """
        Args:
            default_strategy: 默认策略 (auto/structured/semantic/fixed)
            chunk_size: 分块大小
            chunk_overlap: 分块重叠
        """
        self.default_strategy = default_strategy
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # 初始化各策略分块器
        self.structured_splitter = StructuredSplitter(max_chunk_size=chunk_size * 2)
        self.semantic_splitter = SemanticSplitter(target_chunk_size=chunk_size)
        self.fixed_splitter = FixedSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def split(
        self,
        parsed_data: Dict,
        strategy: str = "auto",
    ) -> List[Dict[str, Any]]:
        """执行分块

        Args:
            parsed_data: 解析数据 {
                "text": str,
                "sections": List,
                "tables": List,
                "page_number": int,
            }
            strategy: 分块策略

        Returns:
            分块列表（字典格式）
        """
        if strategy == "auto":
            strategy = self._select_strategy(parsed_data)

        # 执行对应策略
        if strategy == "structured":
            chunks = self.structured_splitter.split(parsed_data)
            return self._normalize_chunks(chunks, strategy)

        elif strategy == "semantic":
            text = parsed_data.get("text", "")
            page_number = parsed_data.get("page_number", 1)
            chunks = self.semantic_splitter.split(text, page_number)
            return self._normalize_chunks(chunks, strategy)

        else:  # fixed
            text = parsed_data.get("text", "")
            page_number = parsed_data.get("page_number", 1)
            chunks = self.fixed_splitter.split(text, page_number)
            return self._normalize_chunks(chunks, strategy)

    def _normalize_chunks(self, chunks: List, strategy: str) -> List[Dict[str, Any]]:
        """标准化分块输出格式

        Args:
            chunks: 分块列表（不同类型）
            strategy: 策略名称

        Returns:
            统一格式的字典列表
        """
        normalized = []

        for i, chunk in enumerate(chunks):
            chunk_dict = {
                "chunk_index": i,
                "clause_id": f"chunk_{i}",  # 添加 clause_id 以便后续匹配
                "content": chunk.content,
                "content_length": chunk.content_length,
                "page_number": chunk.page_number,
                "strategy": strategy,
            }

            # 提取策略特定字段
            if hasattr(chunk, 'chunk_type'):
                chunk_dict["chunk_type"] = chunk.chunk_type
            if hasattr(chunk, 'semantic_type'):
                chunk_dict["position_type"] = chunk.semantic_type
            if hasattr(chunk, 'section_title'):
                chunk_dict["section_title"] = chunk.section_title
            if hasattr(chunk, 'section_level'):
                chunk_dict["section_level"] = chunk.section_level

            # 合并元数据
            if hasattr(chunk, 'metadata') and chunk.metadata:
                chunk_dict.update(chunk.metadata)

            normalized.append(chunk_dict)

        return normalized

    def _select_strategy(self, parsed_data: Dict) -> str:
        """自动选择分块策略

        Args:
            parsed_data: 解析数据

        Returns:
            策略名称
        """
        text = parsed_data.get("text", "")
        sections = parsed_data.get("sections", [])
        tables = parsed_data.get("tables", [])

        text_length = len(text)
        has_structure = len(sections) > 0
        section_count = len(sections)

        # 判断逻辑
        # 1. 有明确章节结构 + 长文档 → 结构化分块
        if has_structure and text_length > self.LONG_DOC_THRESHOLD:
            return "structured"

        # 2. 有一定结构（3+章节） → 结构化分块
        if section_count >= self.STRUCTURE_HINT_THRESHOLD:
            return "structured"

        # 3. 中长文档 → 语义分块
        if text_length > self.MEDIUM_DOC_THRESHOLD:
            return "semantic"

        # 4. 短文档 → 固定大小分块
        return "fixed"

    def get_strategy_info(self, parsed_data: Dict) -> Dict[str, Any]:
        """获取策略选择信息

        Args:
            parsed_data: 解析数据

        Returns:
            策略信息 {
                "selected_strategy": str,
                "reason": str,
                "text_length": int,
                "section_count": int,
            }
        """
        text = parsed_data.get("text", "")
        sections = parsed_data.get("sections", [])

        selected = self._select_strategy(parsed_data)

        reason_map = {
            "structured": "检测到章节结构，使用结构化分块",
            "semantic": "中长文档，使用语义分块",
            "fixed": "短文档，使用固定大小分块",
        }

        return {
            "selected_strategy": selected,
            "reason": reason_map[selected],
            "text_length": len(text),
            "section_count": len(sections),
            "thresholds": {
                "long_doc": self.LONG_DOC_THRESHOLD,
                "medium_doc": self.MEDIUM_DOC_THRESHOLD,
                "structure_hint": self.STRUCTURE_HINT_THRESHOLD,
            },
        }