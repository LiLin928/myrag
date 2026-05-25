"""Master Agent 单元测试"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.agents.master_agent import MasterAgent, TaskDispatchInput


class TestMasterAgent:
    """Master Agent 测试"""

    def test_task_dispatch_input_schema(self):
        """测试任务分发输入 Schema"""
        input_data = TaskDispatchInput(
            task_type="document_review",
            task_description="审核合同文档",
            context={"document_id": "doc_001"}
        )
        assert input_data.task_type == "document_review"
        assert input_data.task_description == "审核合同文档"
        assert input_data.context == {"document_id": "doc_001"}

    def test_task_dispatch_input_default_context(self):
        """测试默认 context"""
        input_data = TaskDispatchInput(
            task_type="data_analysis",
            task_description="分析数据"
        )
        assert input_data.context == {}

    def test_task_type_validation(self):
        """测试任务类型验证"""
        valid_types = ["document_review", "data_analysis", "nl2sql", "general_chat"]
        for t in valid_types:
            input_data = TaskDispatchInput(task_type=t, task_description="test")
            assert input_data.task_type == t

    def test_invalid_task_type_raises_error(self):
        """测试无效任务类型抛出错误"""
        with pytest.raises(Exception):
            TaskDispatchInput(task_type="invalid_type", task_description="test")

    @pytest.mark.asyncio
    async def test_dispatch_to_document_review(self):
        """测试分发到文档审核 Agent"""
        mock_registry = Mock()
        mock_agent = Mock()
        mock_agent.review = AsyncMock(return_value="审核完成")
        mock_registry.get = Mock(return_value=mock_agent)

        master = MasterAgent(mock_registry)
        result = await master.dispatch_to_document_review(
            TaskDispatchInput(
                task_type="document_review",
                task_description="审核合同",
                context={"document_id": "doc_001", "rules": ["完整性"]}
            )
        )
        assert result == "审核完成"

    @pytest.mark.asyncio
    async def test_dispatch_to_data_analysis(self):
        """测试分发到数据分析 Agent"""
        mock_registry = Mock()
        mock_agent = Mock()
        mock_agent.analyze = AsyncMock(return_value="分析报告")
        mock_registry.get = Mock(return_value=mock_agent)

        master = MasterAgent(mock_registry)
        result = await master.dispatch_to_data_analysis(
            TaskDispatchInput(
                task_type="data_analysis",
                task_description="统计销售数据",
                context={"data_path": "/data/sales.csv"}
            )
        )
        assert result == "分析报告"

    @pytest.mark.asyncio
    async def test_dispatch_to_nl2sql(self):
        """测试分发到 NL2SQL Agent"""
        mock_registry = Mock()
        mock_agent = Mock()
        mock_agent.query = AsyncMock(return_value="查询结果")
        mock_registry.get = Mock(return_value=mock_agent)

        master = MasterAgent(mock_registry)
        result = await master.dispatch_to_nl2sql(
            TaskDispatchInput(
                task_type="nl2sql",
                task_description="查询销售额",
                context={"db_config": {"uri": "sqlite:///test.db"}}
            )
        )
        assert result == "查询结果"

    def test_classify_task_document_review(self):
        """测试任务分类 - 文档审核"""
        mock_registry = Mock()
        master = MasterAgent(mock_registry)

        result = master.classify_task("审核这份合同文档")
        assert result == "document_review"

        result = master.classify_task("校验发票是否完整")
        assert result == "document_review"

    def test_classify_task_data_analysis(self):
        """测试任务分类 - 数据分析"""
        mock_registry = Mock()
        master = MasterAgent(mock_registry)

        result = master.classify_task("分析销售数据趋势")
        assert result == "data_analysis"

        result = master.classify_task("生成统计图表")
        assert result == "data_analysis"

    def test_classify_task_nl2sql(self):
        """测试任务分类 - NL2SQL"""
        mock_registry = Mock()
        master = MasterAgent(mock_registry)

        result = master.classify_task("查询有多少订单")
        assert result == "nl2sql"

    def test_classify_task_general_chat(self):
        """测试任务分类 - 通用对话"""
        mock_registry = Mock()
        master = MasterAgent(mock_registry)

        result = master.classify_task("你好，介绍一下 MyRAG")
        assert result == "general_chat"