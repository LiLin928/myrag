"""Agent Registry 单元测试"""

import pytest
from app.agents.agent_registry import AgentRegistry


class TestAgentRegistry:
    """Agent Registry 测试"""

    def test_singleton_pattern(self):
        """测试单例模式 - 多次实例化返回同一对象"""
        registry1 = AgentRegistry()
        registry2 = AgentRegistry()
        assert registry1 is registry2

    def test_register_agent(self):
        """测试注册 Agent"""
        registry = AgentRegistry()
        mock_agent = {"name": "test_agent", "execute": lambda x: x}
        registry.register("test", mock_agent)
        assert registry.has("test")

    def test_get_agent(self):
        """测试获取 Agent"""
        registry = AgentRegistry()
        mock_agent = {"name": "mock"}
        registry.register("mock", mock_agent)
        retrieved = registry.get("mock")
        assert retrieved is mock_agent

    def test_get_nonexistent_agent(self):
        """测试获取不存在 Agent 返回 None"""
        registry = AgentRegistry()
        assert registry.get("nonexistent") is None

    def test_unregister_agent(self):
        """测试注销 Agent"""
        registry = AgentRegistry()
        mock_agent = {"name": "temp"}
        registry.register("temp", mock_agent)
        registry.unregister("temp")
        assert not registry.has("temp")

    def test_list_agents(self):
        """测试列出所有 Agent"""
        registry = AgentRegistry()
        registry.register("agent1", {"id": 1})
        registry.register("agent2", {"id": 2})
        names = registry.list_agents()
        assert "agent1" in names
        assert "agent2" in names