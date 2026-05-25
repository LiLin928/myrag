# tests/agents/test_nl2sql_agent.py
"""NL2SQL Agent 单元测试"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.agents.nl2sql_agent import NL2SQLAgent


class TestNL2SQLAgent:
    """NL2SQL Agent 测试"""

    def test_agent_creation_with_db_uri(self):
        """测试使用数据库 URI 创建 Agent"""
        agent = NL2SQLAgent(db_uri="sqlite:///test.db")
        assert agent is not None
        assert hasattr(agent, "query")

    def test_agent_creation_without_db_uri(self):
        """测试无数据库 URI 创建 Agent"""
        agent = NL2SQLAgent()
        assert agent is not None

    def test_format_query_result_basic(self):
        """测试格式化查询结果"""
        agent = NL2SQLAgent()
        result = agent._format_query_result({
            "messages": [Mock(content="SELECT * FROM users")]
        })
        assert isinstance(result, str)

    def test_format_query_result_with_data(self):
        """测试格式化带数据的查询结果"""
        agent = NL2SQLAgent()
        mock_result = {
            "messages": [
                Mock(content="查询结果:\n| id | name |\n| 1 | test |")
            ]
        }
        result = agent._format_query_result(mock_result)
        assert "查询结果" in result

    @pytest.mark.asyncio
    async def test_query_method(self):
        """测试 query 方法"""
        agent = NL2SQLAgent(db_uri="sqlite:///test.db")
        with patch.object(agent, '_agent_invoke', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = {"messages": [Mock(content="查询结果: 100 条记录")]}
            result = await agent.query("查询有多少用户")
            assert result == "查询结果: 100 条记录"

    def test_validate_select_only(self):
        """测试只允许 SELECT 查询"""
        agent = NL2SQLAgent()
        # SQL 验证逻辑
        dangerous_sqls = ["DELETE FROM", "DROP TABLE", "INSERT INTO", "UPDATE SET"]
        for sql in dangerous_sqls:
            assert agent._validate_sql_safe(sql) is False

        safe_sql = "SELECT * FROM users"
        assert agent._validate_sql_safe(safe_sql) is True