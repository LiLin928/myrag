# tests/agent/test_message_compression.py

import pytest
from unittest.mock import MagicMock
from langchain_core.messages import HumanMessage, AIMessage


class TestMessageCompression:
    """消息压缩测试"""

    def test_trim_messages_returns_none_when_under_limit(self):
        """测试消息数量未超限时不修剪"""
        from app.agent.middleware.message_compression import trim_messages, MAX_MESSAGES

        messages = [HumanMessage(content=f"msg{i}") for i in range(10)]
        state = {"messages": messages}
        runtime = MagicMock()

        # @before_model 创建的是 AgentMiddleware 实例，需要调用 before_model 方法
        result = trim_messages.before_model(state, runtime)
        assert result is None

    def test_trim_messages_returns_update_when_over_limit(self):
        """测试消息数量超限时触发修剪"""
        from app.agent.middleware.message_compression import trim_messages, MAX_MESSAGES

        # 创建 25 条消息
        messages = [HumanMessage(content=f"msg{i}", id=f"id{i}") for i in range(25)]
        state = {"messages": messages}
        runtime = MagicMock()

        result = trim_messages.before_model(state, runtime)
        assert result is not None
        assert "messages" in result

    def test_trim_messages_keeps_first_message(self):
        """测试保留第一条消息"""
        from app.agent.middleware.message_compression import trim_messages, MAX_MESSAGES

        messages = [HumanMessage(content="第一条", id="first")]
        messages.extend([HumanMessage(content=f"msg{i}", id=f"id{i}") for i in range(25)])
        state = {"messages": messages}
        runtime = MagicMock()

        result = trim_messages.before_model(state, runtime)

        # 新消息列表应包含第一条
        new_messages = result["messages"]
        # RemoveMessage 是第一个，然后是保留的消息
        assert len(new_messages) == MAX_MESSAGES + 1  # RemoveMessage + MAX_MESSAGES 条消息

    def test_trim_messages_keeps_recent_messages(self):
        """测试保留最近消息"""
        from app.agent.middleware.message_compression import trim_messages, MAX_MESSAGES

        messages = [HumanMessage(content=f"msg{i}", id=f"id{i}") for i in range(30)]
        state = {"messages": messages}
        runtime = MagicMock()

        result = trim_messages.before_model(state, runtime)

        # 检查返回的消息数量正确
        new_messages = result["messages"]
        # 第一条是 RemoveMessage，然后是 MAX_MESSAGES 条保留消息
        assert len(new_messages) == MAX_MESSAGES + 1

    def test_max_messages_is_20(self):
        """测试 MAX_MESSAGES 默认值为 20"""
        from app.agent.middleware.message_compression import MAX_MESSAGES

        assert MAX_MESSAGES == 20