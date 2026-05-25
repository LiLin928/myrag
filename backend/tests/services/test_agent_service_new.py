# tests/services/test_agent_service_new.py

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.services.agent_service import AgentService


class TestAgentServiceNew:
    """改造后的 Agent Service 测试"""

    @pytest.mark.asyncio
    async def test_agent_service_init(self):
        """测试 AgentService 初始化"""
        with patch("app.services.agent_service.get_checkpointer") as mock_get_checkpointer:
            mock_get_checkpointer.return_value = MagicMock()
            service = AgentService()

            assert service.checkpointer is not None
            assert service._agent is None

    @pytest.mark.asyncio
    async def test_get_agent_lazy_load(self):
        """测试 Agent 懒加载"""
        with patch("app.services.agent_service.create_myrag_agent") as mock_create:
            mock_create.return_value = MagicMock()
            with patch("app.services.agent_service.get_checkpointer") as mock_get_checkpointer:
                mock_get_checkpointer.return_value = MagicMock()
                service = AgentService()

                # 首次获取应创建 Agent
                agent = await service.get_agent()

                assert agent is not None
                assert service._agent is not None
                mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_method(self):
        """测试 chat 方法"""
        with patch("app.services.agent_service.create_myrag_agent") as mock_create_agent:
            with patch("app.services.agent_service.get_checkpointer") as mock_get_checkpointer:
                mock_get_checkpointer.return_value = MagicMock()

                mock_agent = MagicMock()
                mock_message = MagicMock()
                mock_message.type = "ai"
                mock_message.content = "回复内容"
                mock_agent.invoke = AsyncMock(return_value={
                    "messages": [mock_message]
                })
                mock_create_agent.return_value = mock_agent

                service = AgentService()

                result = await service.chat(
                    thread_id="test-thread",
                    message="你好",
                    user_id="user-1",
                )

                assert result is not None
                assert "response" in result
                assert result["response"] == "回复内容"
                assert "messages" in result

    @pytest.mark.asyncio
    async def test_continue_conversation(self):
        """测试继续对话方法"""
        with patch("app.services.agent_service.create_myrag_agent") as mock_create_agent:
            with patch("app.services.agent_service.get_checkpointer") as mock_get_checkpointer:
                mock_get_checkpointer.return_value = MagicMock()

                mock_agent = MagicMock()
                mock_message = MagicMock()
                mock_message.type = "ai"
                mock_message.content = "继续回复"
                mock_agent.invoke = AsyncMock(return_value={
                    "messages": [mock_message]
                })
                mock_create_agent.return_value = mock_agent

                service = AgentService()

                result = await service.continue_conversation(
                    thread_id="test-thread",
                    message="继续",
                )

                assert result is not None
                assert result["response"] == "继续回复"

    @pytest.mark.asyncio
    async def test_resume_from_interrupt(self):
        """测试中断恢复"""
        with patch("app.services.agent_service.create_myrag_agent") as mock_create:
            with patch("app.services.agent_service.get_checkpointer") as mock_get_checkpointer:
                mock_get_checkpointer.return_value = MagicMock()

                mock_agent = MagicMock()
                mock_agent.update_state = AsyncMock()
                mock_message = MagicMock()
                mock_message.type = "ai"
                mock_message.content = "已批准执行"
                mock_agent.invoke = AsyncMock(return_value={
                    "messages": [mock_message]
                })
                mock_create.return_value = mock_agent

                service = AgentService()

                result = await service.resume_from_interrupt(
                    thread_id="test-thread",
                    decision="approve",
                )

                # 应调用 update_state 和 invoke
                mock_agent.update_state.assert_called_once()
                assert result["decision"] == "approve"

    @pytest.mark.asyncio
    async def test_resume_from_interrupt_with_edit(self):
        """测试中断恢复带编辑参数"""
        with patch("app.services.agent_service.create_myrag_agent") as mock_create:
            with patch("app.services.agent_service.get_checkpointer") as mock_get_checkpointer:
                mock_get_checkpointer.return_value = MagicMock()

                mock_agent = MagicMock()
                mock_agent.update_state = AsyncMock()
                mock_message = MagicMock()
                mock_message.type = "ai"
                mock_message.content = "已使用编辑参数执行"
                mock_agent.invoke = AsyncMock(return_value={
                    "messages": [mock_message]
                })
                mock_create.return_value = mock_agent

                service = AgentService()

                edited_args = {"param1": "new_value"}
                result = await service.resume_from_interrupt(
                    thread_id="test-thread",
                    decision="edit",
                    edited_args=edited_args,
                )

                # 应调用 update_state 并传递编辑参数
                mock_agent.update_state.assert_called_once()
                call_args = mock_agent.update_state.call_args
                assert "__edited_args__" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_get_conversation_history(self):
        """测试获取对话历史"""
        with patch("app.services.agent_service.create_myrag_agent") as mock_create:
            with patch("app.services.agent_service.get_checkpointer") as mock_get_checkpointer:
                mock_get_checkpointer.return_value = MagicMock()

                mock_agent = MagicMock()
                mock_state = MagicMock()
                mock_message1 = MagicMock()
                mock_message1.type = "human"
                mock_message1.content = "用户消息"
                mock_message1.tool_calls = None

                mock_message2 = MagicMock()
                mock_message2.type = "ai"
                mock_message2.content = "AI 回复"
                mock_message2.tool_calls = None

                mock_state.values = {"messages": [mock_message1, mock_message2]}
                mock_agent.get_state = AsyncMock(return_value=mock_state)
                mock_create.return_value = mock_agent

                service = AgentService()

                history = await service.get_conversation_history(
                    thread_id="test-thread",
                )

                assert len(history) == 2
                assert history[0]["role"] == "human"
                assert history[1]["role"] == "ai"

    @pytest.mark.asyncio
    async def test_get_pending_interrupt(self):
        """测试获取待处理中断"""
        with patch("app.services.agent_service.create_myrag_agent") as mock_create:
            with patch("app.services.agent_service.get_checkpointer") as mock_get_checkpointer:
                mock_get_checkpointer.return_value = MagicMock()

                mock_agent = MagicMock()
                mock_state = MagicMock()
                mock_task = {"id": "task-1", "name": "sensitive_tool"}
                mock_state.tasks = [mock_task]
                mock_agent.get_state = AsyncMock(return_value=mock_state)
                mock_create.return_value = mock_agent

                service = AgentService()

                result = await service.get_pending_interrupt(
                    thread_id="test-thread",
                )

                assert result is not None
                assert result["thread_id"] == "test-thread"
                assert "task" in result

    @pytest.mark.asyncio
    async def test_get_pending_interrupt_no_tasks(self):
        """测试无待处理中断时返回 None"""
        with patch("app.services.agent_service.create_myrag_agent") as mock_create:
            with patch("app.services.agent_service.get_checkpointer") as mock_get_checkpointer:
                mock_get_checkpointer.return_value = MagicMock()

                mock_agent = MagicMock()
                mock_state = MagicMock()
                mock_state.tasks = []
                mock_agent.get_state = AsyncMock(return_value=mock_state)
                mock_create.return_value = mock_agent

                service = AgentService()

                result = await service.get_pending_interrupt(
                    thread_id="test-thread",
                )

                assert result is None

    @pytest.mark.asyncio
    async def test_global_service_instance(self):
        """测试全局服务实例"""
        from app.services.agent_service import agent_service

        assert agent_service is not None
        assert isinstance(agent_service, AgentService)