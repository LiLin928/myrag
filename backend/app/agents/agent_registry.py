"""Agent 注册中心 - 单例模式管理所有 Agent"""

from __future__ import annotations

from typing import Dict, Any, Optional, List


class AgentRegistry:
    """Agent 注册中心（单例模式）

    负责管理所有 Agent 实例的注册、获取、注销。
    """

    _instance: Optional[AgentRegistry] = None
    _agents: Dict[str, Any] = {}

    def __new__(cls):
        """单例模式 - 确保全局唯一实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents = {}
        return cls._instance

    def register(self, name: str, agent: Any) -> None:
        """注册 Agent

        Args:
            name: Agent 名称
            agent: Agent 实例
        """
        self._agents[name] = agent

    def unregister(self, name: str) -> None:
        """注销 Agent

        Args:
            name: Agent 名称
        """
        if name in self._agents:
            del self._agents[name]

    def get(self, name: str) -> Optional[Any]:
        """获取 Agent

        Args:
            name: Agent 名称

        Returns:
            Agent 实例，不存在则返回 None
        """
        return self._agents.get(name)

    def has(self, name: str) -> bool:
        """检查 Agent 是否存在

        Args:
            name: Agent 名称

        Returns:
            是否存在
        """
        return name in self._agents

    def list_agents(self) -> List[str]:
        """列出所有已注册 Agent 名称

        Returns:
            Agent 名称列表
        """
        return list(self._agents.keys())

    def clear(self) -> None:
        """清空所有 Agent（用于测试）"""
        self._agents.clear()