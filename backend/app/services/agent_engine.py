"""Agent 执行引擎"""

from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import Tool
import uuid

from app.models.agent import Agent
from app.models.agent_binding import AgentKnowledgeBinding, AgentToolBinding, AgentSkillBinding
from app.agent.agent_factory import create_myrag_agent
from app.graphs.checkpointer import get_checkpointer
from app.config import get_settings


class AgentEngine:
    """Agent 执行引擎"""

    def __init__(self, agent: Agent, knowledge_bindings: List[AgentKnowledgeBinding]):
        self.agent = agent
        self.knowledge_bindings = knowledge_bindings
        self.settings = get_settings()
        self.checkpointer = get_checkpointer()
        self._compiled_agent = None

    async def initialize(self):
        """初始化引擎"""
        # 使用现有的 create_myrag_agent，传入自定义工具
        tools = await self._load_tools()

        self._compiled_agent = create_myrag_agent(
            checkpointer=self.checkpointer,
            system_prompt=self.agent.system_prompt,
            tools=tools if tools else None,
        )

    async def _load_tools(self) -> List[Tool]:
        """加载绑定的工具"""
        from app.tools.tool_registry import get_all_tools

        # 获取所有可用工具
        all_tools = get_all_tools()

        # 如果 Agent 没有启用工具或没有绑定，返回空列表
        if not self.agent.use_tools:
            return []

        # TODO: 根据 AgentToolBinding 筛选工具
        # 当前简化实现：返回所有工具
        return all_tools

    async def chat(self, message: str, thread_id: str = None) -> Dict[str, Any]:
        """执行对话"""
        if not self._compiled_agent:
            await self.initialize()

        thread_id = thread_id or str(uuid.uuid4())

        # 执行
        result = await self._compiled_agent.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            {"configurable": {"thread_id": thread_id}},
        )

        # 提取响应
        messages = result.get("messages", [])
        last_message = messages[-1] if messages else None

        # 检查是否有知识库检索结果（简化版暂不实现）
        sources = []
        tool_calls = []

        # 从消息中提取工具调用信息
        for msg in messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append({
                        "tool": tc.get('name', ''),
                        "args": tc.get('args', {}),
                        "result": None,  # 简化版不捕获结果
                    })

        return {
            "thread_id": thread_id,
            "response": last_message.content if last_message else "",
            "sources": sources,
            "tool_calls": tool_calls,
        }

    async def chat_stream(self, message: str, thread_id: str = None):
        """流式执行对话

        Args:
            message: 用户消息
            thread_id: 会话 ID

        Yields:
            流式事件
        """
        if not self._compiled_agent:
            await self.initialize()

        thread_id = thread_id or str(uuid.uuid4())

        # 流式执行
        async for event in self._compiled_agent.astream_events(
            {"messages": [HumanMessage(content=message)]},
            {"configurable": {"thread_id": thread_id}},
            version="v2",
        ):
            yield event

    async def get_state(self, thread_id: str) -> Dict[str, Any]:
        """获取会话状态

        Args:
            thread_id: 会话 ID

        Returns:
            会话状态
        """
        if not self._compiled_agent:
            await self.initialize()

        state = await self._compiled_agent.aget_state(
            {"configurable": {"thread_id": thread_id}}
        )
        return state

    async def update_state(
        self,
        thread_id: str,
        messages: List[Any] = None,
        values: Dict[str, Any] = None,
    ) -> None:
        """更新会话状态

        Args:
            thread_id: 会话 ID
            messages: 要追加的消息
            values: 要更新的值
        """
        if not self._compiled_agent:
            await self.initialize()

        if messages:
            await self._compiled_agent.aupdate_state(
                {"configurable": {"thread_id": thread_id}},
                {"messages": messages},
            )

        if values:
            await self._compiled_agent.aupdate_state(
                {"configurable": {"thread_id": thread_id}},
                values,
            )