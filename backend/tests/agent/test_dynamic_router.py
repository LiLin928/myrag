# tests/agent/test_dynamic_router.py

import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage


class TestDynamicRouter:
    """动态模型路由测试"""

    def test_get_last_user_text_returns_string_content(self):
        """测试获取用户消息文本（字符串格式）"""
        from app.agent.middleware.dynamic_router import _get_last_user_text

        messages = [
            HumanMessage(content="你好"),
            AIMessage(content="你好！"),
            HumanMessage(content="请帮我分析"),
        ]

        result = _get_last_user_text(messages)
        assert result == "请帮我分析"

    def test_get_last_user_text_returns_empty_when_no_user_message(self):
        """测试无用户消息时返回空字符串"""
        from app.agent.middleware.dynamic_router import _get_last_user_text

        messages = [
            AIMessage(content="你好！"),
        ]

        result = _get_last_user_text(messages)
        assert result == ""

    def test_get_last_user_text_handles_multimodal_content(self):
        """测试处理多模态消息"""
        from app.agent.middleware.dynamic_router import _get_last_user_text

        messages = [
            HumanMessage(content=[
                {"type": "text", "text": "请分析这张图片"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,xxx"}}
            ]),
        ]

        result = _get_last_user_text(messages)
        assert result == "请分析这张图片"

    def test_is_complex_query_by_message_count(self):
        """测试根据消息数量判断复杂度"""
        from app.agent.middleware.dynamic_router import _is_complex_query

        messages = [HumanMessage(content=f"msg{i}") for i in range(15)]
        last_user = "简单问题"

        result = _is_complex_query(messages, last_user)
        assert result is True  # 消息数 > 10

    def test_is_complex_query_by_text_length(self):
        """测试根据文本长度判断复杂度"""
        from app.agent.middleware.dynamic_router import _is_complex_query

        messages = [HumanMessage(content="你好")]
        last_user = "这是一个超过一百二十个字符的很长的问题描述需要详细分析..." * 2

        result = _is_complex_query(messages, last_user)
        assert result is True  # 文本 > 120

    def test_is_complex_query_by_keywords(self):
        """测试根据关键词判断复杂度"""
        from app.agent.middleware.dynamic_router import _is_complex_query

        messages = [HumanMessage(content="你好")]
        last_user = "请帮我推导这个数学公式"

        result = _is_complex_query(messages, last_user)
        assert result is True  # 包含 "推导"

    def test_is_simple_query(self):
        """测试简单问题判断"""
        from app.agent.middleware.dynamic_router import _is_complex_query

        messages = [HumanMessage(content="你好")]
        last_user = "今天天气怎么样"

        result = _is_complex_query(messages, last_user)
        assert result is False