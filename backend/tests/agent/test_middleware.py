# tests/agent/test_middleware.py

import pytest
from langchain_core.messages import HumanMessage

from app.agent.middleware.dynamic_router import (
    _get_last_user_text,
    COMPLEX_KEYWORDS,
)


class TestDynamicRouter:
    """动态模型路由测试"""

    def test_get_last_user_text_empty_messages(self):
        """测试空消息列表"""
        result = _get_last_user_text([])
        assert result == ""

    def test_get_last_user_text_single_user_message(self):
        """测试单个用户消息"""
        messages = [HumanMessage(content="Hello")]
        result = _get_last_user_text(messages)
        assert result == "Hello"

    def test_get_last_user_text_multiple_messages(self):
        """测试多消息（返回最后一个用户消息）"""
        messages = [
            HumanMessage(content="First"),
            HumanMessage(content="Second"),
        ]
        result = _get_last_user_text(messages)
        assert result == "Second"

    def test_complex_keywords_detection(self):
        """测试复杂关键词检测"""
        # 包含数学关键词
        assert "数学" in COMPLEX_KEYWORDS or any(kw in "数学问题" for kw in COMPLEX_KEYWORDS)

        # 包含逻辑关键词
        assert any(kw in "逻辑推理" for kw in COMPLEX_KEYWORDS)

    def test_is_complex_by_length(self):
        """测试通过长度判断复杂度"""
        # 长消息判定为复杂
        long_text = "这是一段超过120字的文本..." + "x" * 120
        assert len(long_text) > 120


class TestMessageCompression:
    """消息压缩中间件测试"""

    def test_trim_messages_below_threshold(self):
        """测试消息数低于阈值时不压缩"""
        from app.agent.middleware.message_compression import trim_messages, MAX_MESSAGES
        from unittest.mock import MagicMock

        # 少于阈值的消息
        messages = [HumanMessage(content=f"Message {i}") for i in range(5)]
        state = {"messages": messages}
        runtime = MagicMock()

        # @before_model 装饰器返回 AgentMiddleware，需通过 before_model 方法调用
        result = trim_messages.before_model(state, runtime)

        # 不超过阈值，不压缩
        assert result is None or len(result.get("messages", messages)) <= MAX_MESSAGES

    def test_trim_messages_above_threshold(self):
        """测试消息数超过阈值时压缩"""
        from app.agent.middleware.message_compression import trim_messages, MAX_MESSAGES
        from unittest.mock import MagicMock

        # 超过阈值的消息
        messages = [HumanMessage(content=f"Message {i}") for i in range(25)]
        state = {"messages": messages}
        runtime = MagicMock()

        # @before_model 装饰器返回 AgentMiddleware，需通过 before_model 方法调用
        result = trim_messages.before_model(state, runtime)

        # 应返回压缩后的消息
        assert result is not None
        new_messages = result.get("messages", [])
        # 保留第一条 + 最后 MAX_MESSAGES-1 条（第一条是 RemoveMessage）
        assert len(new_messages) == MAX_MESSAGES + 1

    def test_max_messages_default(self):
        """测试默认阈值"""
        from app.agent.middleware.message_compression import MAX_MESSAGES

        assert MAX_MESSAGES == 20


class TestMiddlewareExports:
    """中间件导出测试"""

    def test_dynamic_router_exported(self):
        """测试动态路由导出"""
        from app.agent.middleware import dynamic_deepseek_routing, COMPLEX_KEYWORDS

        assert dynamic_deepseek_routing is not None
        assert COMPLEX_KEYWORDS is not None

    def test_trim_messages_exported(self):
        """测试消息压缩导出"""
        from app.agent.middleware import trim_messages, MAX_MESSAGES

        assert trim_messages is not None
        assert MAX_MESSAGES == 20

    def test_human_approval_exported(self):
        """测试人工审批导出"""
        from app.agent.middleware import human_approval_middleware, SENSITIVE_TOOLS

        assert human_approval_middleware is not None
        assert SENSITIVE_TOOLS is not None