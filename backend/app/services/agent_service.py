# app/services/agent_service.py

"""Agent 服务

管理 Agent 对话的创建、执行、恢复
"""

from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage

from app.agent.agent_factory import create_myrag_agent, get_default_checkpointer
from app.config import get_settings


class AgentService:
    """Agent 服务"""

    def __init__(self):
        self._agent = None
        self._agent_config: Optional[Dict] = None
        self.settings = get_settings()

    async def get_agent(self, config: Optional[Dict] = None):
        """获取 Agent 实例（支持配置）

        Args:
            config: Agent 配置，包含：
                - enable_dynamic_router: 是否启用动态路由
                - enable_message_compression: 是否启用消息压缩
                - enable_human_approval: 是否启用人工审批

        Returns:
            Agent 实例
        """
        if self._agent is None or self._agent_config != config:
            self._agent_config = config
            self._agent = create_myrag_agent(
                checkpointer=get_default_checkpointer(),
                enable_dynamic_router=config.get("enable_dynamic_router", True) if config else True,
                enable_message_compression=config.get("enable_message_compression", True) if config else True,
                enable_human_approval=config.get("enable_human_approval", True) if config else True,
            )
        return self._agent

    async def chat(
        self,
        thread_id: str,
        message: str,
        user_id: str,
        system_prompt: Optional[str] = None,
        config: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """执行对话

        Args:
            thread_id: 会话线程 ID
            message: 用户消息
            user_id: 用户 ID
            system_prompt: 系统提示
            config: Agent 配置（中间件开关）

        Returns:
            对话结果，包含：
            - thread_id: 会话 ID
            - response: 响应内容
            - messages: 消息列表
            - requires_approval: 是否需要人工审批（可选）
            - action_requests: 待审批操作列表（可选）
        """
        agent = await self.get_agent(config)

        invoke_config = {"configurable": {"thread_id": thread_id}}

        # 执行
        result = await agent.invoke(
            {"messages": [HumanMessage(content=message)]},
            invoke_config,
        )

        # 处理人工审批中断
        if "__interrupt__" in result:
            return self._format_interrupt_response(thread_id, result)

        # 获取响应
        messages = result.get("messages", [])
        last_message = messages[-1] if messages else None

        return {
            "thread_id": thread_id,
            "response": last_message.content if last_message else "",
            "messages": [
                {"role": msg.type, "content": msg.content}
                for msg in messages
            ],
        }

    def _format_interrupt_response(self, thread_id: str, result: Dict) -> Dict:
        """格式化中断响应

        将 __interrupt__ 格式化为用户友好的审批请求

        Args:
            thread_id: 会话 ID
            result: Agent 执行结果（包含 __interrupt__）

        Returns:
            格式化后的响应
        """
        interrupts = result.get("__interrupt__", [])
        action_requests = []

        for interrupt in interrupts:
            # 解析中断信息
            tool_name = interrupt.get("tool_name", "未知工具")
            tool_args = interrupt.get("args", {})
            reason = interrupt.get("reason", "需要人工审批")

            action_requests.append({
                "tool_name": tool_name,
                "args": tool_args,
                "reason": reason,
            })

        # 构建格式化的审批文本
        if len(action_requests) == 1:
            req = action_requests[0]
            formatted_approval_text = (
                f"工具调用需要审批确认：\n\n"
                f"**工具**: {req['tool_name']}\n"
                f"**参数**: {req['args']}\n"
                f"**原因**: {req['reason']}\n\n"
                f"请选择：批准 / 拒绝 / 编辑参数"
            )
        else:
            lines = ["以下工具调用需要审批确认："]
            for i, req in enumerate(action_requests, 1):
                lines.append(f"\n{i}. **{req['tool_name']}**")
                lines.append(f"   参数: {req['args']}")
                lines.append(f"   原因: {req['reason']}")
            lines.append("\n请选择：批准 / 拒绝 / 编辑参数")
            formatted_approval_text = "\n".join(lines)

        return {
            "thread_id": thread_id,
            "response": formatted_approval_text,
            "requires_approval": True,
            "action_requests": action_requests,
        }

    async def continue_conversation(
        self,
        thread_id: str,
        message: str,
        config: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """继续对话

        Args:
            thread_id: 会话线程 ID
            message: 用户消息
            config: Agent 配置

        Returns:
            对话结果
        """
        agent = await self.get_agent(config)

        invoke_config = {"configurable": {"thread_id": thread_id}}

        result = await agent.invoke(
            {"messages": [HumanMessage(content=message)]},
            invoke_config,
        )

        # 处理人工审批中断
        if "__interrupt__" in result:
            return self._format_interrupt_response(thread_id, result)

        messages = result.get("messages", [])
        last_message = messages[-1] if messages else None

        return {
            "thread_id": thread_id,
            "response": last_message.content if last_message else "",
        }

    async def resume_from_interrupt(
        self,
        thread_id: str,
        decision: str,
        edited_args: Optional[Dict[str, Any]] = None,
        config: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """从中断点恢复

        用于 Human-in-the-Loop 场景，用户审批后恢复执行。

        Args:
            thread_id: 会话线程 ID
            decision: 审批决策 ("approve", "reject", "edit")
            edited_args: 编辑后的参数（仅 decision="edit" 时有效）
            config: Agent 配置

        Returns:
            执行结果
        """
        agent = await self.get_agent(config)
        invoke_config = {"configurable": {"thread_id": thread_id}}

        # 构建状态更新
        state_update = {"decision": decision}
        if edited_args:
            state_update["edited_input"] = edited_args

        # 更新状态以恢复执行
        await agent.update_state(invoke_config, state_update)

        # 继续执行
        result = await agent.invoke(None, invoke_config)

        # 处理可能的新中断
        if "__interrupt__" in result:
            return self._format_interrupt_response(thread_id, result)

        messages = result.get("messages", [])
        last_message = messages[-1] if messages else None

        return {
            "thread_id": thread_id,
            "decision": decision,
            "response": last_message.content if last_message else "",
        }

    async def get_conversation_history(
        self,
        thread_id: str,
        config: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """获取对话历史

        Args:
            thread_id: 会话线程 ID
            config: Agent 配置

        Returns:
            消息列表
        """
        agent = await self.get_agent(config)
        invoke_config = {"configurable": {"thread_id": thread_id}}

        state = await agent.get_state(invoke_config)

        messages = state.values.get("messages", [])

        return [
            {
                "role": msg.type,
                "content": msg.content,
                "tool_calls": getattr(msg, "tool_calls", None),
            }
            for msg in messages
        ]

    async def get_pending_interrupt(
        self,
        thread_id: str,
        config: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """获取待处理的中断

        Args:
            thread_id: 会话线程 ID
            config: Agent 配置

        Returns:
            中断信息，若无则返回 None
        """
        agent = await self.get_agent(config)
        invoke_config = {"configurable": {"thread_id": thread_id}}

        state = await agent.get_state(invoke_config)

        # 检查是否有待处理的任务
        tasks = state.tasks
        if tasks:
            # 返回第一个待处理任务的信息
            task = tasks[0]
            return {
                "thread_id": thread_id,
                "task": task,
            }

        return None


# 全局服务实例
agent_service = AgentService()