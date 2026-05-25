# app/agents/document_review_agent.py
"""DocumentReview Agent - 文档审核专家"""

from typing import Dict, Any, Optional, List


class DocumentReviewAgent:
    """文档审核 Agent - 完整性检查、格式校验、业务规则验证

    使用多模态解析服务解析文档，然后执行审核规则。
    """

    DEFAULT_RULES = ["完整性检查", "格式校验"]

    def __init__(self, parser_service: Optional[Any] = None):
        """初始化文档审核 Agent

        Args:
            parser_service: 多模态解析服务实例（可选）
        """
        self.parser_service = parser_service
        self._agent = None  # LangChain Agent 实例（延迟初始化）

    def _check_completeness(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """完整性检查

        Args:
            document: 文档数据（包含 markdown 和 metadata）

        Returns:
            检查结果
        """
        markdown = document.get("markdown", "")
        metadata = document.get("metadata", {})

        # 检查基本完整性指标
        pages = metadata.get("pages", 0)
        content_length = len(markdown)

        if pages > 0 and content_length > 100:
            return {
                "rule": "完整性检查",
                "status": "pass",
                "details": f"文档完整：{pages} 页，{content_length} 字符"
            }
        else:
            return {
                "rule": "完整性检查",
                "status": "fail",
                "details": f"文档不完整：{pages} 页，{content_length} 字符"
            }

    def _check_format(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """格式校验

        Args:
            document: 文档数据

        Returns:
            检查结果
        """
        markdown = document.get("markdown", "")

        # 检查基本格式指标
        has_title = markdown.startswith("#") or "##" in markdown
        has_structure = "\n\n" in markdown or "\n" in markdown

        if has_title and has_structure:
            return {
                "rule": "格式校验",
                "status": "pass",
                "details": "文档格式正确：包含标题和结构"
            }
        else:
            return {
                "rule": "格式校验",
                "status": "fail",
                "details": "文档格式异常：缺少标题或结构"
            }

    def _generate_review_report(self, check_results: List[Dict[str, Any]]) -> str:
        """生成审核报告

        Args:
            check_results: 各规则检查结果列表

        Returns:
            审核报告文本
        """
        report = "# 文档审核报告\n\n"

        pass_count = sum(1 for r in check_results if r["status"] == "pass")
        fail_count = len(check_results) - pass_count

        report += f"## 总体结果\n\n"
        report += f"- 通过: {pass_count}\n"
        report += f"- 失败: {fail_count}\n\n"

        report += "## 详细检查结果\n\n"
        for result in check_results:
            status_icon = "✓" if result["status"] == "pass" else "✗"
            report += f"### {result['rule']} {status_icon}\n\n"
            report += f"{result['details']}\n\n"

        return report

    async def review(
        self,
        document_id: str,
        rules: Optional[List[str]] = None
    ) -> str:
        """执行文档审核

        Args:
            document_id: 文档 ID
            rules: 审核规则列表（可选，默认使用 DEFAULT_RULES）

        Returns:
            审核报告
        """
        rules = rules or self.DEFAULT_RULES

        # 解析文档
        document_data = {}
        if self.parser_service:
            try:
                document_data = await self.parser_service.parse_document(document_id)
            except Exception:
                document_data = {"markdown": "", "metadata": {}}

        # 执行检查
        check_results = []
        for rule in rules:
            if rule == "完整性检查":
                check_results.append(self._check_completeness(document_data))
            elif rule == "格式校验":
                check_results.append(self._check_format(document_data))
            else:
                check_results.append({
                    "rule": rule,
                    "status": "skip",
                    "details": "规则未实现"
                })

        # 生成报告
        return self._generate_review_report(check_results)