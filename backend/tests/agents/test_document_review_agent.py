# tests/agents/test_document_review_agent.py
"""DocumentReview Agent 单元测试"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.agents.document_review_agent import DocumentReviewAgent


class TestDocumentReviewAgent:
    """文档审核 Agent 测试"""

    def test_agent_creation(self):
        """测试 Agent 创建"""
        mock_parser = Mock()
        agent = DocumentReviewAgent(parser_service=mock_parser)
        assert agent is not None
        assert hasattr(agent, "review")

    def test_agent_creation_without_parser(self):
        """测试无 parser_service 创建 Agent"""
        agent = DocumentReviewAgent()
        assert agent is not None

    @pytest.mark.asyncio
    async def test_review_method(self):
        """测试 review 方法"""
        mock_parser = Mock()
        mock_parser.parse_document = AsyncMock(return_value={
            "markdown": "# 文档内容\n完整内容...",
            "metadata": {"pages": 10}
        })

        agent = DocumentReviewAgent(parser_service=mock_parser)

        result = await agent.review(
            document_id="doc_001",
            rules=["完整性检查", "格式校验"]
        )

        assert isinstance(result, str)
        assert "审核结果" in result or "报告" in result

    def test_check_completeness(self):
        """测试完整性检查"""
        agent = DocumentReviewAgent()

        # 完整文档（内容长度需超过 100 字符）
        complete_doc = {
            "markdown": """这是一份完整的测试文档内容，包含了足够的文字内容以满足完整性检查的要求。
文档内容包括标题、正文和结论三个部分。
这里是正文部分的详细内容，包含了多个段落和丰富的信息。
最后是结论部分，总结文档的核心要点和关键信息。
整体文档结构完整，内容充实，符合完整性检查的标准要求。""",
            "metadata": {"pages": 5}
        }
        result = agent._check_completeness(complete_doc)
        assert result["status"] == "pass"

        # 不完整文档
        incomplete_doc = {
            "markdown": "",
            "metadata": {"pages": 0}
        }
        result = agent._check_completeness(incomplete_doc)
        assert result["status"] == "fail"

    def test_check_format(self):
        """测试格式校验"""
        agent = DocumentReviewAgent()

        # 格式正确
        valid_format = {
            "markdown": "# 标题\n## 章节\n正文内容",
            "metadata": {}
        }
        result = agent._check_format(valid_format)
        assert result["status"] == "pass"

    def test_generate_review_report(self):
        """测试生成审核报告"""
        agent = DocumentReviewAgent()

        check_results = [
            {"rule": "完整性检查", "status": "pass", "details": "文档完整"},
            {"rule": "格式校验", "status": "pass", "details": "格式正确"},
        ]

        report = agent._generate_review_report(check_results)
        assert "审核报告" in report
        assert "完整性检查" in report
        assert "格式校验" in report