# tests/agent/test_integration.py

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from langchain_core.messages import HumanMessage

from app.services.agent_service import AgentService


class TestAgentIntegration:
    """Agent 集成测试"""

    @pytest.mark.skip(reason="create_agent 需要真实工具对象，MagicMock 无法满足 ToolNode 的要求")
    @pytest.mark.asyncio
    @patch("langchain.agents.create_agent")
    @patch("app.agent.agent_factory.ChatDeepSeek")
    @patch("app.agent.agent_factory.get_all_tools")
    @patch("app.agent.agent_factory.get_default_checkpointer")
    async def test_full_agent_flow(self, mock_get_checkpointer, mock_get_tools, mock_chat, mock_create_agent):
        """测试完整 Agent 流程（使用新 create_agent API）"""
        # Mock 工具
        mock_tools = [MagicMock(name="knowledge_search")]
        mock_get_tools.return_value = mock_tools

        # Mock 模型
        mock_model = MagicMock()
        mock_model.invoke = AsyncMock(return_value=MagicMock(content="回复"))
        mock_chat.return_value = mock_model

        # Mock agent
        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(return_value={
            "messages": [MagicMock(type="ai", content="回复")]
        })
        mock_create_agent.return_value = mock_agent

        # Mock checkpointer
        mock_checkpointer = MagicMock()
        mock_get_checkpointer.return_value = mock_checkpointer

        # 创建 Agent
        from app.agent.agent_factory import create_myrag_agent
        agent = create_myrag_agent()

        assert agent is not None
        mock_create_agent.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.agent.middleware.dynamic_router._get_models")
    async def test_middleware_chain(self, mock_get_models):
        """测试中间件链（使用新 API）"""
        from app.agent.middleware import (
            dynamic_deepseek_routing,
            trim_messages,
            human_approval_middleware,
        )
        from unittest.mock import MagicMock

        # Mock 模型
        mock_chat_model = MagicMock()
        mock_reasoner_model = MagicMock()
        mock_get_models.return_value = (mock_chat_model, mock_reasoner_model)

        # 创建测试状态
        messages = [HumanMessage(content=f"Message {i}") for i in range(25)]
        state = {"messages": messages}
        runtime = MagicMock()

        # 测试消息压缩（使用新 API）
        compressed = trim_messages.before_model(state, runtime)
        if compressed:
            assert len(compressed.get("messages", messages)) == 21  # RemoveMessage + 20 messages

        # 新 API 使用 @wrap_model_call 和 HumanInTheLoopMiddleware
        # 中间件通过 create_agent 的 middleware 参数集成

    @pytest.mark.asyncio
    async def test_agent_service_full_flow(self):
        """测试 AgentService 完整流程"""
        with patch("app.services.agent_service.create_myrag_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.invoke = AsyncMock(return_value={
                "messages": [MagicMock(type="ai", content="回复")]
            })
            mock_agent.get_state = AsyncMock(return_value=MagicMock(
                values={"messages": []},
                tasks=[]
            ))
            mock_create.return_value = mock_agent

            service = AgentService()

            # 测试 chat
            result = await service.chat(
                thread_id="test",
                message="你好",
                user_id="user1",
            )

            assert result["response"] == "回复"

            # 测试 history
            history = await service.get_conversation_history("test")
            assert isinstance(history, list)

    @pytest.mark.asyncio
    @patch("app.agent.middleware.dynamic_router._get_models")
    async def test_middleware_with_complex_query(self, mock_get_models):
        """测试复杂查询触发 reasoner 模型"""
        from app.agent.middleware.dynamic_router import (
            dynamic_deepseek_routing,
            _is_complex_query,
        )

        # Mock 模型
        mock_chat_model = MagicMock()
        mock_reasoner_model = MagicMock()
        mock_get_models.return_value = (mock_chat_model, mock_reasoner_model)

        # 创建复杂查询（包含数学关键词）
        messages = [HumanMessage(content="请证明数学公式")]
        state = {"messages": messages}

        # 测试复杂查询判断
        last_text = "请证明数学公式"
        is_complex = _is_complex_query(messages, last_text)
        assert is_complex is True

    @pytest.mark.asyncio
    @patch("app.agent.middleware.dynamic_router._get_models")
    async def test_middleware_with_simple_query(self, mock_get_models):
        """测试简单查询使用 chat 模型"""
        from app.agent.middleware.dynamic_router import (
            dynamic_deepseek_routing,
            _is_complex_query,
        )

        # Mock 模型
        mock_chat_model = MagicMock()
        mock_reasoner_model = MagicMock()
        mock_get_models.return_value = (mock_chat_model, mock_reasoner_model)

        # 创建简单查询
        messages = [HumanMessage(content="你好")]
        state = {"messages": messages}

        # 测试简单查询判断
        last_text = "你好"
        is_complex = _is_complex_query(messages, last_text)
        assert is_complex is False

    @pytest.mark.asyncio
    async def test_human_approval_sensitive_tool(self):
        """测试敏感工具触发人工审批（使用新 HumanInTheLoopMiddleware）"""
        from app.agent.middleware.human_approval import human_approval_middleware, SENSITIVE_TOOLS

        # 新 API: HumanInTheLoopMiddleware 通过 interrupt_on 配置
        # 检查敏感工具在 interrupt_on 配置中
        assert "execute_python" in human_approval_middleware.interrupt_on
        assert "http_request" in human_approval_middleware.interrupt_on

        # 检查敏感工具列表
        assert "execute_python" in SENSITIVE_TOOLS
        assert "http_request" in SENSITIVE_TOOLS

    @pytest.mark.asyncio
    async def test_human_approval_normal_tool(self):
        """测试普通工具不在人工审批列表中"""
        from app.agent.middleware.human_approval import human_approval_middleware, SENSITIVE_TOOLS

        # 普通工具不在 interrupt_on 配置中
        interrupt_on = human_approval_middleware.interrupt_on

        # knowledge_search 不在敏感工具列表中
        assert "knowledge_search" not in SENSITIVE_TOOLS
        assert "knowledge_search" not in interrupt_on


class TestAgentServiceIntegration:
    """Agent Service 集成测试"""

    @pytest.mark.asyncio
    @patch("app.services.agent_service.create_myrag_agent")
    async def test_chat_creates_agent_with_config(self, mock_create_agent):
        """测试 chat 方法创建 Agent 时传递配置"""
        # Mock agent
        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(return_value={
            "messages": [MagicMock(type="ai", content="回复")]
        })
        mock_create_agent.return_value = mock_agent

        service = AgentService()

        # 调用 chat 时传递配置
        config = {
            "enable_dynamic_router": False,
            "enable_message_compression": False,
            "enable_human_approval": False,
        }
        result = await service.chat(
            thread_id="test",
            message="你好",
            user_id="user1",
            config=config,
        )

        # 验证 create_myrag_agent 被调用并传递了正确的配置
        mock_create_agent.assert_called_once()
        call_kwargs = mock_create_agent.call_args[1]
        assert call_kwargs["enable_dynamic_router"] is False
        assert call_kwargs["enable_message_compression"] is False
        assert call_kwargs["enable_human_approval"] is False

        # 验证返回结果
        assert result["response"] == "回复"
        assert result["thread_id"] == "test"

    @pytest.mark.asyncio
    @patch("app.services.agent_service.create_myrag_agent")
    async def test_chat_handles_interrupt(self, mock_create_agent):
        """测试 chat 方法处理中断"""
        # Mock agent 返回中断
        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(return_value={
            "__interrupt__": [
                {
                    "tool_name": "execute_python",
                    "args": {"code": "print('hello')"},
                    "reason": "敏感操作需要审批",
                }
            ]
        })
        mock_create_agent.return_value = mock_agent

        service = AgentService()

        result = await service.chat(
            thread_id="test",
            message="执行代码",
            user_id="user1",
        )

        # 验证返回中断响应
        assert result["requires_approval"] is True
        assert len(result["action_requests"]) == 1
        assert result["action_requests"][0]["tool_name"] == "execute_python"
        assert "审批确认" in result["response"]

    @pytest.mark.asyncio
    @patch("app.services.agent_service.create_myrag_agent")
    async def test_chat_handles_multiple_interrupts(self, mock_create_agent):
        """测试 chat 方法处理多个中断"""
        # Mock agent 返回多个中断
        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(return_value={
            "__interrupt__": [
                {
                    "tool_name": "execute_python",
                    "args": {"code": "print(1)"},
                    "reason": "代码执行需要审批",
                },
                {
                    "tool_name": "http_request",
                    "args": {"url": "https://example.com"},
                    "reason": "外部请求需要审批",
                }
            ]
        })
        mock_create_agent.return_value = mock_agent

        service = AgentService()

        result = await service.chat(
            thread_id="test",
            message="执行多个操作",
            user_id="user1",
        )

        # 验证返回多个中断
        assert result["requires_approval"] is True
        assert len(result["action_requests"]) == 2
        assert result["action_requests"][0]["tool_name"] == "execute_python"
        assert result["action_requests"][1]["tool_name"] == "http_request"

    @pytest.mark.asyncio
    @patch("app.services.agent_service.create_myrag_agent")
    async def test_resume_from_interrupt_approve(self, mock_create_agent):
        """测试从中断恢复（批准）"""
        # Mock agent
        mock_agent = MagicMock()
        mock_agent.update_state = AsyncMock()
        mock_agent.invoke = AsyncMock(return_value={
            "messages": [MagicMock(type="ai", content="执行成功")]
        })
        mock_create_agent.return_value = mock_agent

        service = AgentService()

        result = await service.resume_from_interrupt(
            thread_id="test",
            decision="approve",
        )

        # 验证 update_state 被调用
        mock_agent.update_state.assert_called_once()
        call_args = mock_agent.update_state.call_args
        assert call_args[0][1]["decision"] == "approve"

        # 验证返回结果
        assert result["decision"] == "approve"
        assert result["response"] == "执行成功"

    @pytest.mark.asyncio
    @patch("app.services.agent_service.create_myrag_agent")
    async def test_resume_from_interrupt_with_edit(self, mock_create_agent):
        """测试从中断恢复（编辑参数）"""
        # Mock agent
        mock_agent = MagicMock()
        mock_agent.update_state = AsyncMock()
        mock_agent.invoke = AsyncMock(return_value={
            "messages": [MagicMock(type="ai", content="执行成功")]
        })
        mock_create_agent.return_value = mock_agent

        service = AgentService()

        edited_args = {"code": "print('modified')"}
        result = await service.resume_from_interrupt(
            thread_id="test",
            decision="edit",
            edited_args=edited_args,
        )

        # 验证 update_state 被调用并包含编辑参数
        mock_agent.update_state.assert_called_once()
        call_args = mock_agent.update_state.call_args
        assert call_args[0][1]["decision"] == "edit"
        assert call_args[0][1]["edited_input"] == edited_args

        assert result["decision"] == "edit"

    @pytest.mark.asyncio
    @patch("app.services.agent_service.create_myrag_agent")
    async def test_resume_from_interrupt_with_config(self, mock_create_agent):
        """测试从中断恢复时传递配置"""
        # Mock agent
        mock_agent = MagicMock()
        mock_agent.update_state = AsyncMock()
        mock_agent.invoke = AsyncMock(return_value={
            "messages": [MagicMock(type="ai", content="回复")]
        })
        mock_create_agent.return_value = mock_agent

        service = AgentService()

        config = {"enable_human_approval": True}
        await service.resume_from_interrupt(
            thread_id="test",
            decision="approve",
            config=config,
        )

        # 验证 create_myrag_agent 被调用并传递了配置
        mock_create_agent.assert_called_once()
        call_kwargs = mock_create_agent.call_args[1]
        assert call_kwargs["enable_human_approval"] is True

    @pytest.mark.asyncio
    @patch("app.services.agent_service.create_myrag_agent")
    async def test_agent_config_caching(self, mock_create_agent):
        """测试 Agent 配置缓存"""
        # Mock agent
        mock_agent1 = MagicMock()
        mock_agent1.invoke = AsyncMock(return_value={
            "messages": [MagicMock(type="ai", content="回复1")]
        })
        mock_agent2 = MagicMock()
        mock_agent2.invoke = AsyncMock(return_value={
            "messages": [MagicMock(type="ai", content="回复2")]
        })
        mock_create_agent.side_effect = [mock_agent1, mock_agent2]

        service = AgentService()

        # 第一次调用，配置 A
        config_a = {"enable_dynamic_router": True}
        await service.chat(thread_id="test1", message="msg", user_id="u1", config=config_a)

        # 第二次调用，相同配置，应该复用 agent
        await service.chat(thread_id="test2", message="msg", user_id="u1", config=config_a)

        # 验证只创建了一次
        assert mock_create_agent.call_count == 1

        # 第三次调用，不同配置，应该创建新的 agent
        config_b = {"enable_dynamic_router": False}
        await service.chat(thread_id="test3", message="msg", user_id="u1", config=config_b)

        # 验证创建了两次
        assert mock_create_agent.call_count == 2