"""条款级分块器

将文档内容分割为条款级分块，保留语义完整性
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import re


@dataclass
class ClauseBlock:
    """条款级分块结构"""

    clause_id: str           # 条款唯一标识
    clause_type: Optional[str]  # 条款类型（定义/权利/义务/违约等）
    clause_title: Optional[str]  # 条款标题
    content: str             # 条款完整内容
    page_number: int         # 页码
    parent_clause_id: Optional[str]  # 父条款 ID（层级关系）
    metadata: Dict[str, Any]  # 其他元数据


class ClauseSplitter:
    """条款级分块器"""

    # 条款标题正则模式
    CLAUSE_PATTERNS = [
        r"第[一二三四五六七八九十百千万]+[条款项章节]",  # 中文条款
        r"第\d+[条款项章节]",                            # 数字条款
        r"[一二三四五六七八九十]+[、.]",                 # 中文序号
        r"\d+[、.]",                                     # 数字序号
        r"(\d+\.\d+)",                                   # 多级条款
    ]

    # 条款类型识别关键词
    CLAUSE_TYPE_KEYWORDS = {
        "定义": ["定义", "术语", "含义"],
        "权利": ["有权", "权利", "享有", "可以"],
        "义务": ["应当", "必须", "义务", "承担"],
        "违约": ["违约", "责任", "赔偿", "罚款"],
        "期限": ["期限", "日期", "时间", "日内"],
        "金额": ["金额", "价格", "费用", "元"],
        "保密": ["保密", "机密", "不披露"],
        "终止": ["终止", "解除", "结束", "届满"],
    }

    def split(self, content_blocks: List[Dict]) -> List[ClauseBlock]:
        """将文档内容块分割为条款级分块

        Args:
            content_blocks: 解析输出的内容块列表

        Returns:
            条款级分块列表
        """
        clauses = []
        current_clause = None
        clause_counter = 0

        for block in content_blocks:
            text = block.get("content", "")
            page = block.get("page_number", 1)

            # 检测条款标题
            clause_title = self._detect_clause_title(text)

            if clause_title:
                # 保存上一个条款
                if current_clause:
                    clauses.append(current_clause)

                # 开始新条款
                clause_counter += 1
                clause_type = self._detect_clause_type(text)

                current_clause = ClauseBlock(
                    clause_id=f"clause_{clause_counter}",
                    clause_type=clause_type,
                    clause_title=clause_title,
                    content=text,
                    page_number=page,
                    parent_clause_id=self._get_parent_id(clause_title, clauses),
                    metadata={"block_type": block.get("type")},
                )
            elif current_clause:
                # 续接当前条款内容
                current_clause.content += "\n" + text

        # 保存最后一个条款
        if current_clause:
            clauses.append(current_clause)

        return clauses

    def _detect_clause_title(self, text: str) -> Optional[str]:
        """检测条款标题

        Args:
            text: 文本内容

        Returns:
            条款标题，未检测到则返回 None
        """
        for pattern in self.CLAUSE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                # 提取完整标题（通常在行首）
                line = text.split("\n")[0]
                return line.strip()
        return None

    def _detect_clause_type(self, text: str) -> Optional[str]:
        """检测条款类型

        Args:
            text: 文本内容

        Returns:
            条款类型
        """
        for clause_type, keywords in self.CLAUSE_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return clause_type
        return None

    def _get_parent_id(self, clause_title: str, existing_clauses: List[ClauseBlock]) -> Optional[str]:
        """获取父条款 ID（层级关系）

        Args:
            clause_title: 当前条款标题
            existing_clauses: 已存在的条款列表

        Returns:
            父条款 ID
        """
        # 检测多级条款（如 1.1, 1.2）
        multi_level_match = re.search(r"(\d+)\.\d+", clause_title)
        if multi_level_match:
            parent_num = multi_level_match.group(1)
            for clause in existing_clauses:
                if re.search(rf"第{parent_num}[条款章节]", clause.clause_title or ""):
                    return clause.clause_id

        # 检测子条款（如 "（一）"）
        sub_clause_match = re.search(r"[（(][一二三四五六七八九十]+[）)]", clause_title)
        if sub_clause_match:
            # 查找最近的上一级条款
            if existing_clauses:
                return existing_clauses[-1].clause_id

        return None

    def to_dict_list(self, clauses: List[ClauseBlock]) -> List[Dict[str, Any]]:
        """转换为字典列表（便于存储）

        Args:
            clauses: ClauseBlock 列表

        Returns:
            字典列表
        """
        return [asdict(clause) for clause in clauses]