"""多 Agent 协作集成测试"""

import pytest
from unittest.mock import Mock, AsyncMock

from app.agents.agent_registry import AgentRegistry
from app.agents.master_agent import MasterAgent
from app.agents.data_analysis_agent import DataAnalysisAgent
from app.agents.nl2sql_agent import NL2SQLAgent
from app.agents.document_review_agent import DocumentReviewAgent
from app.services.multi_agent_service import MultiAgentService


class TestMultiAgentIntegration:
    """多 Agent 协作集成测试"""

    @pytest.fixture(autouse=True)
    def setup_registry(self):
        """每个测试前清空 Registry"""
        registry = AgentRegistry()
        registry.clear()
        yield registry
        # 测试后再次清空
        registry.clear()

    def test_full_agent_registration_flow(self):
        """测试完整 Agent 注册流程"""
        registry = AgentRegistry()

        # 注册所有 Agent
        registry.register("document_review", DocumentReviewAgent())
        registry.register("data_analysis", DataAnalysisAgent())
        registry.register("nl2sql", NL2SQLAgent())
        registry.register("master", MasterAgent(registry))

        # 验证所有 Agent 已注册
        assert len(registry.list_agents()) == 4
        assert registry.has("master")
        assert registry.has("document_review")
        assert registry.has("data_analysis")
        assert registry.has("nl2sql")

    @pytest.mark.asyncio
    async def test_master_dispatch_to_document_review(self):
        """测试 Master 分发到文档审核 Agent"""
        registry = AgentRegistry()

        # 创建并注册文档审核 Agent
        mock_parser = Mock()
        mock_parser.parse_document = AsyncMock(return_value={
            "markdown": "# 测试文档\n完整内容",
            "metadata": {"pages": 5}
        })
        review_agent = DocumentReviewAgent(parser_service=mock_parser)
        registry.register("document_review", review_agent)

        # 创建 Master Agent
        master = MasterAgent(registry)

        # 执行任务分发
        result = await master.process("审核合同文档", {"document_id": "doc_001"})
        assert "审核报告" in result

    @pytest.mark.asyncio
    async def test_master_dispatch_to_document_review_with_rules(self):
        """测试 Master 分发到文档审核 Agent 并带自定义规则"""
        registry = AgentRegistry()

        # 创建并注册文档审核 Agent
        mock_parser = Mock()
        mock_parser.parse_document = AsyncMock(return_value={
            "markdown": "# 合同文档\n## 第一章\n内容详情\n\n## 第二章\n更多内容",
            "metadata": {"pages": 10}
        })
        review_agent = DocumentReviewAgent(parser_service=mock_parser)
        registry.register("document_review", review_agent)

        # 创建 Master Agent
        master = MasterAgent(registry)

        # 执行任务分发带自定义规则
        result = await master.process("审核合同文档", {
            "document_id": "doc_002",
            "rules": ["完整性检查", "格式校验"]
        })
        assert "审核报告" in result
        assert "完整性检查" in result

    @pytest.mark.asyncio
    async def test_master_dispatch_to_data_analysis(self):
        """测试 Master 分发到数据分析 Agent"""
        registry = AgentRegistry()

        # Mock LLM 服务
        mock_llm = Mock()
        mock_llm.chat = AsyncMock(return_value="分析结果: 销售趋势上升")

        # 注册数据分析 Agent
        analysis_agent = DataAnalysisAgent(llm_service=mock_llm)
        registry.register("data_analysis", analysis_agent)

        # 创建 Master Agent
        master = MasterAgent(registry)

        # 执行任务分发
        result = await master.process("分析销售数据", {"data_path": "test.csv"})
        assert "分析" in result

    @pytest.mark.asyncio
    async def test_master_dispatch_to_data_analysis_no_llm(self):
        """测试 Master 分发到数据分析 Agent（无 LLM 服务）"""
        registry = AgentRegistry()

        # 注册数据分析 Agent（无 LLM）
        analysis_agent = DataAnalysisAgent()
        registry.register("data_analysis", analysis_agent)

        # 创建 Master Agent
        master = MasterAgent(registry)

        # 执行任务分发
        result = await master.process("分析销售数据", {"data_path": "test.csv"})
        assert "LLM" in result or "服务" in result

    @pytest.mark.asyncio
    async def test_master_dispatch_to_nl2sql(self):
        """测试 Master 分发到 NL2SQL Agent"""
        registry = AgentRegistry()

        # 注册 NL2SQL Agent
        nl2sql_agent = NL2SQLAgent(db_uri="sqlite:///test.db")
        registry.register("nl2sql", nl2sql_agent)

        # 创建 Master Agent
        master = MasterAgent(registry)

        # 执行任务分发
        result = await master.process("查询订单数量", {"db_config": {"uri": "sqlite:///test.db"}})
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_master_dispatch_to_nl2sql_no_db(self):
        """测试 Master 分发到 NL2SQL Agent（无数据库配置）"""
        registry = AgentRegistry()

        # 注册 NL2SQL Agent（无数据库）
        nl2sql_agent = NL2SQLAgent()
        registry.register("nl2sql", nl2sql_agent)

        # 创建 Master Agent
        master = MasterAgent(registry)

        # 执行任务分发（无 db_config）
        result = await master.process("查询订单数量", {})
        assert "未配置" in result or "数据库" in result

    @pytest.mark.asyncio
    async def test_master_general_chat(self):
        """测试 Master 处理通用对话"""
        registry = AgentRegistry()
        master = MasterAgent(registry)

        # 测试通用对话
        result = await master.process("你好，介绍一下 MyRAG")
        assert "通用对话" in result

    @pytest.mark.asyncio
    async def test_service_full_workflow(self):
        """测试服务层完整工作流"""
        service = MultiAgentService()

        # 初始化服务
        service.initialize()

        # 验证初始化成功
        agents = service.get_available_agents()
        assert "master" in agents
        assert "document_review" in agents
        assert "data_analysis" in agents
        assert "nl2sql" in agents

    @pytest.mark.asyncio
    async def test_service_process_document_review_task(self):
        """测试服务层处理文档审核任务"""
        registry = AgentRegistry()
        registry.clear()

        # Mock parser
        mock_parser = Mock()
        mock_parser.parse_document = AsyncMock(return_value={
            "markdown": "# 测试文档\n完整内容",
            "metadata": {"pages": 5}
        })

        # 创建带 mock parser 的 DocumentReview Agent
        review_agent = DocumentReviewAgent(parser_service=mock_parser)

        # 注册 Agent
        registry.register("document_review", review_agent)

        # 注册 Master
        master = MasterAgent(registry)
        registry.register("master", master)

        # 创建服务
        service = MultiAgentService()
        service._initialized = True  # 标记已初始化

        result = await service.process_task("审核发票", {"document_id": "doc_001"})
        assert "审核报告" in result

    @pytest.mark.asyncio
    async def test_service_dispatch_to_agent(self):
        """测试服务层直接分发到 Agent"""
        registry = AgentRegistry()
        registry.clear()

        # Mock LLM
        mock_llm = Mock()
        mock_llm.chat = AsyncMock(return_value="数据分析结果")

        # 注册 Agent
        registry.register("data_analysis", DataAnalysisAgent(llm_service=mock_llm))
        registry.register("master", MasterAgent(registry))

        # 创建服务
        service = MultiAgentService(llm_service=mock_llm)
        service._initialized = True

        result = await service.dispatch_to_agent(
            "data_analysis",
            task_description="分析销售趋势",
            context={"month": "2024-01"}
        )
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_service_dispatch_to_nonexistent_agent(self):
        """测试服务层分发到不存在的 Agent"""
        registry = AgentRegistry()
        registry.clear()

        # 注册 Master
        registry.register("master", MasterAgent(registry))

        # 创建服务
        service = MultiAgentService()
        service._initialized = True

        result = await service.dispatch_to_agent("unknown_agent")
        assert "未注册" in result or "不存在" in result

    def test_task_classification_and_dispatch(self):
        """测试任务分类和分发"""
        registry = AgentRegistry()
        master = MasterAgent(registry)

        # 测试分类逻辑
        assert master.classify_task("审核发票") == "document_review"
        assert master.classify_task("校验合同完整性") == "document_review"
        assert master.classify_task("检查文档格式") == "document_review"

        assert master.classify_task("分析销售趋势") == "data_analysis"
        assert master.classify_task("生成统计图表") == "data_analysis"
        assert master.classify_task("数据报告") == "data_analysis"

        assert master.classify_task("查询订单数量") == "nl2sql"
        assert master.classify_task("有多少用户") == "nl2sql"
        assert master.classify_task("对比销售额") == "nl2sql"

        assert master.classify_task("你好") == "general_chat"
        assert master.classify_task("介绍一下系统") == "general_chat"

        # 边界情况：包含多个关键词的任务
        # "数据库报表" 包含 "数据"，会被分类为 data_analysis
        assert master.classify_task("数据库报表") == "data_analysis"

    def test_get_agent_status_all_initialized(self):
        """测试获取所有 Agent 状态"""
        registry = AgentRegistry()
        registry.clear()

        service = MultiAgentService()
        service.initialize()

        status = service.get_agent_status()
        assert "master" in status
        assert "data_analysis" in status
        assert "nl2sql" in status
        assert "document_review" in status

        # 验证状态结构
        for agent_name, agent_status in status.items():
            assert "registered" in agent_status
            assert agent_status["registered"] is True
            assert "type" in agent_status

    def test_registry_singleton_pattern(self):
        """测试 Registry 单例模式"""
        registry1 = AgentRegistry()
        registry2 = AgentRegistry()

        assert registry1 is registry2

        # 注册后两个实例都能访问
        registry1.register("test_agent", Mock())
        assert registry2.has("test_agent")

        # 清空后两个实例都清空
        registry1.clear()
        assert not registry2.has("test_agent")

    @pytest.mark.asyncio
    async def test_multi_agent_sequential_tasks(self):
        """测试多 Agent 顺序处理多个任务"""
        registry = AgentRegistry()
        registry.clear()

        # 注册所有 Agent
        mock_parser = Mock()
        mock_parser.parse_document = AsyncMock(return_value={
            "markdown": "# 文档\n内容",
            "metadata": {"pages": 5}
        })
        registry.register("document_review", DocumentReviewAgent(parser_service=mock_parser))
        registry.register("master", MasterAgent(registry))

        # 处理多个任务
        result1 = await MasterAgent(registry).process("审核合同A")
        result2 = await MasterAgent(registry).process("你好")

        assert "审核报告" in result1
        assert "通用对话" in result2

    @pytest.mark.asyncio
    async def test_service_auto_initialize_on_process(self):
        """测试服务自动初始化"""
        registry = AgentRegistry()
        registry.clear()

        service = MultiAgentService()
        # 不手动调用 initialize

        # process_task 会自动初始化
        result = await service.process_task("你好")
        assert "通用对话" in result

        # 验证已初始化
        assert service._initialized is True
        agents = service.get_available_agents()
        assert len(agents) > 0