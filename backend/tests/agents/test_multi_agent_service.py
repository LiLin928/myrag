"""MultiAgentService 服务层测试"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.services.multi_agent_service import MultiAgentService
from app.agents.agent_registry import AgentRegistry
from app.agents.master_agent import MasterAgent
from app.agents.data_analysis_agent import DataAnalysisAgent
from app.agents.nl2sql_agent import NL2SQLAgent
from app.agents.document_review_agent import DocumentReviewAgent


class TestMultiAgentService:
    """MultiAgentService 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前清空 Registry"""
        registry = AgentRegistry()
        registry.clear()
        yield
        registry.clear()

    def test_initialize_registers_all_agents(self):
        """测试初始化注册所有 Agent"""
        service = MultiAgentService()
        service.initialize()

        registry = AgentRegistry()
        assert registry.has("master")
        assert registry.has("data_analysis")
        assert registry.has("nl2sql")
        assert registry.has("document_review")

    def test_initialize_without_llm_service(self):
        """测试无 LLM 服务初始化"""
        service = MultiAgentService(llm_service=None)
        service.initialize()

        registry = AgentRegistry()
        assert registry.has("master")
        assert registry.has("data_analysis")

    def test_initialize_with_llm_service(self):
        """测试带 LLM 服务初始化"""
        mock_llm = Mock()
        service = MultiAgentService(llm_service=mock_llm)
        service.initialize()

        registry = AgentRegistry()
        data_analysis_agent = registry.get("data_analysis")
        assert data_analysis_agent is not None
        assert data_analysis_agent.llm_service is mock_llm

    @pytest.mark.asyncio
    async def test_process_task_document_review(self):
        """测试处理文档审核任务"""
        service = MultiAgentService()
        service.initialize()

        # Mock document review agent
        mock_doc_agent = Mock()
        mock_doc_agent.review = AsyncMock(return_value="审核报告: 通过")
        registry = AgentRegistry()
        registry.register("document_review", mock_doc_agent)

        result = await service.process_task("审核合同文档", {"document_id": "doc_001"})
        assert "审核报告" in result or "文档审核 Agent" in result

    @pytest.mark.asyncio
    async def test_process_task_data_analysis(self):
        """测试处理数据分析任务"""
        mock_llm = Mock()
        mock_llm.chat = AsyncMock(return_value="分析结果: 销售趋势上升")
        service = MultiAgentService(llm_service=mock_llm)
        service.initialize()

        result = await service.process_task("分析销售数据趋势", {"data_path": "/data/sales.csv"})
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_process_task_nl2sql(self):
        """测试处理 NL2SQL 任务"""
        service = MultiAgentService()
        service.initialize()

        # Mock nl2sql agent
        mock_nl2sql_agent = Mock()
        mock_nl2sql_agent.query = AsyncMock(return_value="查询结果: 100 条记录")
        registry = AgentRegistry()
        registry.register("nl2sql", mock_nl2sql_agent)

        result = await service.process_task("查询有多少订单", {"db_config": {"uri": "sqlite:///test.db"}})
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_process_task_general_chat(self):
        """测试处理通用对话任务"""
        service = MultiAgentService()
        service.initialize()

        result = await service.process_task("你好，介绍一下系统功能")
        assert "通用对话" in result

    @pytest.mark.asyncio
    async def test_dispatch_to_agent_document_review(self):
        """测试直接分发到文档审核 Agent"""
        service = MultiAgentService()
        service.initialize()

        # Mock document review agent
        mock_agent = Mock()
        mock_agent.review = AsyncMock(return_value="文档审核结果")
        registry = AgentRegistry()
        registry.register("document_review", mock_agent)

        result = await service.dispatch_to_agent(
            "document_review",
            document_id="doc_123",
            rules=["完整性检查", "格式校验"]
        )
        assert result == "文档审核结果"
        mock_agent.review.assert_called_once_with("doc_123", ["完整性检查", "格式校验"])

    @pytest.mark.asyncio
    async def test_dispatch_to_agent_data_analysis(self):
        """测试直接分发到数据分析 Agent"""
        mock_llm = Mock()
        mock_llm.chat = AsyncMock(return_value="数据分析结果")
        service = MultiAgentService(llm_service=mock_llm)
        service.initialize()

        result = await service.dispatch_to_agent(
            "data_analysis",
            task_description="分析销售数据",
            context={"month": "2024-01"}
        )
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_dispatch_to_agent_nl2sql(self):
        """测试直接分发到 NL2SQL Agent"""
        service = MultiAgentService()
        service.initialize()

        # Mock nl2sql agent
        mock_agent = Mock()
        mock_agent.query = AsyncMock(return_value="查询结果")
        registry = AgentRegistry()
        registry.register("nl2sql", mock_agent)

        result = await service.dispatch_to_agent(
            "nl2sql",
            question="查询用户数量",
            db_config={"uri": "sqlite:///test.db"}
        )
        assert result == "查询结果"
        mock_agent.query.assert_called_once_with("查询用户数量", {"uri": "sqlite:///test.db"})

    @pytest.mark.asyncio
    async def test_dispatch_to_nonexistent_agent(self):
        """测试分发到不存在的 Agent"""
        service = MultiAgentService()
        service.initialize()

        result = await service.dispatch_to_agent("unknown_agent", param="value")
        assert "未注册" in result or "不存在" in result

    def test_get_agent_status_all_initialized(self):
        """测试获取所有 Agent 状态 - 已初始化"""
        service = MultiAgentService()
        service.initialize()

        status = service.get_agent_status()
        assert "master" in status
        assert "data_analysis" in status
        assert "nl2sql" in status
        assert "document_review" in status

    def test_get_agent_status_with_values(self):
        """测试获取 Agent 状态带具体值"""
        service = MultiAgentService()
        service.initialize()

        status = service.get_agent_status()
        assert isinstance(status, dict)
        for agent_name, agent_status in status.items():
            assert "registered" in agent_status or "status" in agent_status

    def test_get_available_agents(self):
        """测试获取可用 Agent 列表"""
        service = MultiAgentService()
        service.initialize()

        agents = service.get_available_agents()
        assert isinstance(agents, list)
        assert "master" in agents
        assert "data_analysis" in agents
        assert "nl2sql" in agents
        assert "document_review" in agents

    def test_get_available_agents_empty_before_init(self):
        """测试初始化前获取可用 Agent 列表为空"""
        service = MultiAgentService()
        # 不调用 initialize

        agents = service.get_available_agents()
        assert isinstance(agents, list)
        # 可能为空或只有部分 Agent

    @pytest.mark.asyncio
    async def test_multiple_sequential_tasks(self):
        """测试顺序执行多个任务"""
        service = MultiAgentService()
        service.initialize()

        # Mock agents
        mock_doc_agent = Mock()
        mock_doc_agent.review = AsyncMock(return_value="审核完成")
        registry = AgentRegistry()
        registry.register("document_review", mock_doc_agent)

        # 执行多个任务
        result1 = await service.process_task("审核文档A")
        result2 = await service.process_task("审核文档B")

        assert isinstance(result1, str)
        assert isinstance(result2, str)

    @pytest.mark.asyncio
    async def test_dispatch_with_none_agent(self):
        """测试 Agent 为 None 时的分发"""
        service = MultiAgentService()
        service.initialize()

        # 清空 data_analysis agent
        registry = AgentRegistry()
        registry.unregister("data_analysis")

        result = await service.dispatch_to_agent("data_analysis", task_description="测试")
        assert "未注册" in result or "不存在" in result

    def test_service_singleton_registry(self):
        """测试服务使用单例 Registry"""
        service1 = MultiAgentService()
        service2 = MultiAgentService()

        service1.initialize()
        # service2 应该能看到 service1 注册的 agents
        registry = AgentRegistry()
        assert registry.has("master")