"""DataAnalysis Agent 单元测试"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.agents.data_analysis_agent import DataAnalysisAgent, AnalysisResult


class TestDataAnalysisAgent:
    """DataAnalysis Agent 测试"""

    def test_analysis_result_schema(self):
        """测试分析结果 Schema"""
        result = AnalysisResult(
            summary="销售数据概要",
            insights=["趋势1", "趋势2"],
            recommendations=["建议1", "建议2"]
        )
        assert result.summary == "销售数据概要"
        assert result.insights == ["趋势1", "趋势2"]
        assert result.recommendations == ["建议1", "建议2"]

    def test_analysis_result_default_values(self):
        """测试默认值"""
        result = AnalysisResult(summary="测试摘要")
        assert result.summary == "测试摘要"
        assert result.insights == []
        assert result.recommendations == []

    @pytest.mark.asyncio
    async def test_analyze_basic(self):
        """测试基本分析功能"""
        mock_llm_service = Mock()
        mock_llm_service.chat = AsyncMock(return_value="分析结果：销售数据呈上升趋势")

        agent = DataAnalysisAgent(llm_service=mock_llm_service)
        result = await agent.analyze("分析销售数据", {"data_source": "sales.csv"})

        assert "销售数据" in result or "趋势" in result or "分析结果" in result

    @pytest.mark.asyncio
    async def test_analyze_with_context(self):
        """测试带上下文的分析"""
        mock_llm_service = Mock()
        mock_llm_service.chat = AsyncMock(return_value="根据上下文分析完成")

        agent = DataAnalysisAgent(llm_service=mock_llm_service)
        result = await agent.analyze(
            "生成统计报告",
            {
                "data_source": "orders.csv",
                "time_range": "2024-01-01 to 2024-12-31",
                "metrics": ["revenue", "orders"]
            }
        )

        assert result is not None
        mock_llm_service.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_empty_description(self):
        """测试空描述"""
        mock_llm_service = Mock()
        mock_llm_service.chat = AsyncMock(return_value="请提供分析任务描述")

        agent = DataAnalysisAgent(llm_service=mock_llm_service)
        result = await agent.analyze("", {})

        assert result is not None

    @pytest.mark.asyncio
    async def test_analyze_with_chart_request(self):
        """测试图表请求"""
        mock_llm_service = Mock()
        mock_llm_service.chat = AsyncMock(return_value="图表生成完成")

        agent = DataAnalysisAgent(llm_service=mock_llm_service)
        result = await agent.analyze("生成销售趋势图表", {"chart_type": "line"})

        assert "图表" in result or "chart" in result.lower() or "生成完成" in result

    def test_build_prompt_basic(self):
        """测试构建提示词"""
        mock_llm_service = Mock()
        agent = DataAnalysisAgent(llm_service=mock_llm_service)

        prompt = agent._build_prompt("分析销售数据", {"data_source": "sales.csv"})

        assert "分析销售数据" in prompt
        assert "sales.csv" in prompt
        assert "数据分析师" in prompt or "分析师" in prompt

    def test_build_prompt_with_metrics(self):
        """测试带指标的提示词"""
        mock_llm_service = Mock()
        agent = DataAnalysisAgent(llm_service=mock_llm_service)

        prompt = agent._build_prompt(
            "统计订单数据",
            {"metrics": ["revenue", "quantity", "users"]}
        )

        assert "revenue" in prompt or "指标" in prompt
        assert "统计订单数据" in prompt

    @pytest.mark.asyncio
    async def test_analyze_without_llm_service(self):
        """测试无 LLM 服务"""
        agent = DataAnalysisAgent(llm_service=None)
        result = await agent.analyze("分析数据", {})

        # 无 LLM 服务时返回默认响应
        assert "需要配置 LLM 服务" in result or "LLM 服务" in result