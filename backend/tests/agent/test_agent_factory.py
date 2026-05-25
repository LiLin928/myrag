# tests/agent/test_agent_factory.py

import pytest
from unittest.mock import MagicMock, patch


class TestAgentFactoryNewAPI:
    """Agent Factory 新 API 测试（create_agent）"""

    @patch("app.agent.agent_factory.create_agent")
    @patch("app.agent.agent_factory.ChatDeepSeek")
    @patch("app.agent.agent_factory.get_all_tools")
    @patch("app.agent.agent_factory.get_default_checkpointer")
    def test_create_agent_uses_create_agent_api(
        self, mock_get_checkpointer, mock_get_tools, mock_chat_deepseek, mock_create_agent
    ):
        """测试使用 create_agent API"""
        mock_model = MagicMock()
        mock_chat_deepseek.return_value = mock_model
        mock_tools = [MagicMock(name="tool1", spec=["name"])]
        mock_get_tools.return_value = mock_tools
        mock_checkpointer = MagicMock()
        mock_get_checkpointer.return_value = mock_checkpointer
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        from app.agent.agent_factory import create_myrag_agent

        agent = create_myrag_agent()

        # 应调用 create_agent 而非 create_react_agent
        mock_create_agent.assert_called_once()
        assert agent is mock_agent

    @patch("app.agent.agent_factory.create_agent")
    @patch("app.agent.agent_factory.ChatDeepSeek")
    @patch("app.agent.agent_factory.get_all_tools")
    @patch("app.agent.agent_factory.get_default_checkpointer")
    def test_create_agent_with_all_middlewares_enabled(
        self, mock_get_checkpointer, mock_get_tools, mock_chat_deepseek, mock_create_agent
    ):
        """测试所有中间件启用"""
        mock_model = MagicMock()
        mock_chat_deepseek.return_value = mock_model
        mock_tools = [MagicMock(name="tool1", spec=["name"])]
        mock_get_tools.return_value = mock_tools
        mock_checkpointer = MagicMock()
        mock_get_checkpointer.return_value = mock_checkpointer
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        from app.agent.agent_factory import create_myrag_agent

        agent = create_myrag_agent(
            enable_dynamic_router=True,
            enable_message_compression=True,
            enable_human_approval=True,
        )

        # 检查 middleware 参数
        call_kwargs = mock_create_agent.call_args[1]
        assert "middleware" in call_kwargs
        middleware_list = call_kwargs["middleware"]
        assert len(middleware_list) == 3

    @patch("app.agent.agent_factory.create_agent")
    @patch("app.agent.agent_factory.ChatDeepSeek")
    @patch("app.agent.agent_factory.get_all_tools")
    @patch("app.agent.agent_factory.get_default_checkpointer")
    def test_create_agent_with_middlewares_disabled(
        self, mock_get_checkpointer, mock_get_tools, mock_chat_deepseek, mock_create_agent
    ):
        """测试中间件禁用"""
        mock_model = MagicMock()
        mock_chat_deepseek.return_value = mock_model
        mock_tools = [MagicMock(name="tool1", spec=["name"])]
        mock_get_tools.return_value = mock_tools
        mock_checkpointer = MagicMock()
        mock_get_checkpointer.return_value = mock_checkpointer
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        from app.agent.agent_factory import create_myrag_agent

        agent = create_myrag_agent(
            enable_dynamic_router=False,
            enable_message_compression=False,
            enable_human_approval=False,
        )

        # middleware 应为空列表
        call_kwargs = mock_create_agent.call_args[1]
        middleware_list = call_kwargs["middleware"]
        assert len(middleware_list) == 0

    @patch("app.agent.agent_factory.create_agent")
    @patch("app.agent.agent_factory.ChatDeepSeek")
    @patch("app.agent.agent_factory.get_all_tools")
    @patch("app.agent.agent_factory.get_default_checkpointer")
    def test_create_agent_with_custom_checkpointer(
        self, mock_get_checkpointer, mock_get_tools, mock_chat_deepseek, mock_create_agent
    ):
        """测试自定义 checkpointer"""
        mock_model = MagicMock()
        mock_chat_deepseek.return_value = mock_model
        mock_tools = [MagicMock(name="tool1", spec=["name"])]
        mock_get_tools.return_value = mock_tools
        custom_checkpointer = MagicMock(name="custom_checkpointer")
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        from app.agent.agent_factory import create_myrag_agent

        agent = create_myrag_agent(checkpointer=custom_checkpointer)

        # 不应调用 get_default_checkpointer
        mock_get_checkpointer.assert_not_called()

        # 检查 checkpointer 参数
        call_kwargs = mock_create_agent.call_args[1]
        assert call_kwargs["checkpointer"] == custom_checkpointer

    @patch("app.agent.agent_factory.create_agent")
    @patch("app.agent.agent_factory.ChatDeepSeek")
    @patch("app.agent.agent_factory.get_all_tools")
    @patch("app.agent.agent_factory.get_default_checkpointer")
    def test_create_agent_passes_system_prompt(
        self, mock_get_checkpointer, mock_get_tools, mock_chat_deepseek, mock_create_agent
    ):
        """测试传递系统提示"""
        mock_model = MagicMock()
        mock_chat_deepseek.return_value = mock_model
        mock_tools = [MagicMock(name="tool1", spec=["name"])]
        mock_get_tools.return_value = mock_tools
        mock_checkpointer = MagicMock()
        mock_get_checkpointer.return_value = mock_checkpointer
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        from app.agent.agent_factory import create_myrag_agent

        custom_prompt = "自定义系统提示"
        agent = create_myrag_agent(system_prompt=custom_prompt)

        # 检查 system_prompt 参数
        call_kwargs = mock_create_agent.call_args[1]
        assert call_kwargs["system_prompt"] == custom_prompt

    @patch("app.agent.agent_factory.create_agent")
    @patch("app.agent.agent_factory.ChatDeepSeek")
    @patch("app.agent.agent_factory.get_all_tools")
    @patch("app.agent.agent_factory.get_default_checkpointer")
    def test_create_agent_with_custom_tools(
        self, mock_get_checkpointer, mock_get_tools, mock_chat_deepseek, mock_create_agent
    ):
        """测试自定义工具列表"""
        mock_model = MagicMock()
        mock_chat_deepseek.return_value = mock_model
        custom_tools = [MagicMock(name="custom_tool", spec=["name"])]
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        from app.agent.agent_factory import create_myrag_agent

        agent = create_myrag_agent(
            checkpointer=custom_tools[0],  # Use as checkpointer to avoid get_default_checkpointer
            tools=custom_tools,
        )

        # Should not call get_all_tools when custom tools provided
        mock_get_tools.assert_not_called()
        # Verify custom tools were used
        call_kwargs = mock_create_agent.call_args[1]
        assert call_kwargs["tools"] == custom_tools

    @patch("app.agent.agent_factory.create_agent")
    @patch("app.agent.agent_factory.ChatDeepSeek")
    @patch("app.agent.agent_factory.get_all_tools")
    @patch("app.agent.agent_factory.get_default_checkpointer")
    def test_create_agent_calls_tool_registry_when_no_tools(
        self, mock_get_checkpointer, mock_get_tools, mock_chat_deepseek, mock_create_agent
    ):
        """测试无自定义工具时调用工具注册表"""
        mock_model = MagicMock()
        mock_chat_deepseek.return_value = mock_model
        mock_tools = [MagicMock(name="tool1", spec=["name"])]
        mock_get_tools.return_value = mock_tools
        mock_checkpointer = MagicMock()
        mock_get_checkpointer.return_value = mock_checkpointer
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        from app.agent.agent_factory import create_myrag_agent

        agent = create_myrag_agent()

        mock_get_tools.assert_called_once()


class TestGetDefaultCheckpointer:
    """get_default_checkpointer 函数测试"""

    @patch("app.graphs.checkpointer.get_checkpointer")
    def test_get_default_checkpointer_returns_postgres_saver(self, mock_get_checkpointer):
        """测试成功返回 PostgresSaver"""
        mock_checkpointer = MagicMock()
        mock_get_checkpointer.return_value = mock_checkpointer

        from app.agent.agent_factory import get_default_checkpointer

        result = get_default_checkpointer()
        assert result is mock_checkpointer

    @patch("app.graphs.checkpointer.get_checkpointer")
    @patch("app.agent.agent_factory.InMemorySaver")
    def test_get_default_checkpointer_fallback_to_memory(self, mock_memory_saver, mock_get_checkpointer):
        """测试 PostgresSaver 失败时回退到 InMemorySaver"""
        mock_get_checkpointer.side_effect = Exception("PostgresSaver 初始化失败")
        mock_memory_instance = MagicMock()
        mock_memory_saver.return_value = mock_memory_instance

        from app.agent.agent_factory import get_default_checkpointer

        result = get_default_checkpointer()
        assert result is mock_memory_instance


class TestMiddlewareIntegration:
    """中间件集成测试"""

    @patch("app.agent.agent_factory.create_agent")
    @patch("app.agent.agent_factory.ChatDeepSeek")
    @patch("app.agent.agent_factory.get_all_tools")
    @patch("app.agent.agent_factory.get_default_checkpointer")
    def test_dynamic_router_middleware_added(
        self, mock_get_checkpointer, mock_get_tools, mock_chat_deepseek, mock_create_agent
    ):
        """测试动态路由中间件被正确添加"""
        mock_model = MagicMock()
        mock_chat_deepseek.return_value = mock_model
        mock_tools = [MagicMock(name="tool1", spec=["name"])]
        mock_get_tools.return_value = mock_tools
        mock_checkpointer = MagicMock()
        mock_get_checkpointer.return_value = mock_checkpointer
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        from app.agent.agent_factory import create_myrag_agent
        from app.agent.middleware import dynamic_deepseek_routing

        agent = create_myrag_agent(enable_dynamic_router=True)

        call_kwargs = mock_create_agent.call_args[1]
        middleware_list = call_kwargs["middleware"]
        assert dynamic_deepseek_routing in middleware_list

    @patch("app.agent.agent_factory.create_agent")
    @patch("app.agent.agent_factory.ChatDeepSeek")
    @patch("app.agent.agent_factory.get_all_tools")
    @patch("app.agent.agent_factory.get_default_checkpointer")
    def test_message_compression_middleware_added(
        self, mock_get_checkpointer, mock_get_tools, mock_chat_deepseek, mock_create_agent
    ):
        """测试消息压缩中间件被正确添加"""
        mock_model = MagicMock()
        mock_chat_deepseek.return_value = mock_model
        mock_tools = [MagicMock(name="tool1", spec=["name"])]
        mock_get_tools.return_value = mock_tools
        mock_checkpointer = MagicMock()
        mock_get_checkpointer.return_value = mock_checkpointer
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        from app.agent.agent_factory import create_myrag_agent
        from app.agent.middleware import trim_messages

        agent = create_myrag_agent(enable_message_compression=True)

        call_kwargs = mock_create_agent.call_args[1]
        middleware_list = call_kwargs["middleware"]
        assert trim_messages in middleware_list

    @patch("app.agent.agent_factory.create_agent")
    @patch("app.agent.agent_factory.ChatDeepSeek")
    @patch("app.agent.agent_factory.get_all_tools")
    @patch("app.agent.agent_factory.get_default_checkpointer")
    def test_human_approval_middleware_added(
        self, mock_get_checkpointer, mock_get_tools, mock_chat_deepseek, mock_create_agent
    ):
        """测试人工审批中间件被正确添加"""
        mock_model = MagicMock()
        mock_chat_deepseek.return_value = mock_model
        mock_tools = [MagicMock(name="tool1", spec=["name"])]
        mock_get_tools.return_value = mock_tools
        mock_checkpointer = MagicMock()
        mock_get_checkpointer.return_value = mock_checkpointer
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        from app.agent.agent_factory import create_myrag_agent
        from app.agent.middleware import human_approval_middleware

        agent = create_myrag_agent(enable_human_approval=True)

        call_kwargs = mock_create_agent.call_args[1]
        middleware_list = call_kwargs["middleware"]
        assert human_approval_middleware in middleware_list

    @patch("app.agent.agent_factory.create_agent")
    @patch("app.agent.agent_factory.ChatDeepSeek")
    @patch("app.agent.agent_factory.get_all_tools")
    @patch("app.agent.agent_factory.get_default_checkpointer")
    def test_middleware_order(
        self, mock_get_checkpointer, mock_get_tools, mock_chat_deepseek, mock_create_agent
    ):
        """测试中间件顺序"""
        mock_model = MagicMock()
        mock_chat_deepseek.return_value = mock_model
        mock_tools = [MagicMock(name="tool1", spec=["name"])]
        mock_get_tools.return_value = mock_tools
        mock_checkpointer = MagicMock()
        mock_get_checkpointer.return_value = mock_checkpointer
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        from app.agent.agent_factory import create_myrag_agent
        from app.agent.middleware import (
            dynamic_deepseek_routing,
            trim_messages,
            human_approval_middleware,
        )

        agent = create_myrag_agent(
            enable_dynamic_router=True,
            enable_message_compression=True,
            enable_human_approval=True,
        )

        call_kwargs = mock_create_agent.call_args[1]
        middleware_list = call_kwargs["middleware"]

        # 验证中间件顺序: dynamic_router -> trim_messages -> human_approval
        assert middleware_list[0] == dynamic_deepseek_routing
        assert middleware_list[1] == trim_messages
        assert middleware_list[2] == human_approval_middleware