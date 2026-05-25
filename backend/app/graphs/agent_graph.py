"""Agent 对话状态机

实现多轮对话的 LangGraph StateGraph，支持：
- LLM 调用
- 工具调用
- 人工介入（中断恢复）
"""

from typing import TypedDict, Annotated, List, Dict, Any, Literal, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import BaseMessage
from operator import add


class AgentState(TypedDict):
    """Agent 对话状态定义

    Attributes:
        thread_id: 会话线程 ID（用于 Checkpointer）
        user_id: 用户 ID
        messages: 对话消息列表
        current_step: 当前步骤
        tool_calls: 待执行的工具调用
        tool_results: 工具执行结果
        context: 执行上下文（项目 ID、配置等）
        error: 错误信息
    """
    thread_id: str
    user_id: str
    messages: Annotated[List[Dict[str, Any]], add]  # 消息列表，使用 add reducer
    current_step: Literal["idle", "thinking", "tool_calling", "responding", "human", "error"]
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    context: Dict[str, Any]
    error: Optional[str]


# 节点函数定义

async def think_node(state: AgentState) -> Dict[str, Any]:
    """思考节点：准备 LLM 调用

    分析当前对话，决定下一步行动
    """
    # TODO: 实现真实 LLM 调用逻辑
    return {
        "current_step": "thinking",
    }


async def call_tools_node(state: AgentState) -> Dict[str, Any]:
    """工具调用节点：执行工具

    根据 tool_calls 执行工具，收集结果
    """
    # TODO: 实现真实工具调用逻辑
    return {
        "current_step": "tool_calling",
        "tool_results": [],
    }


async def respond_node(state: AgentState) -> Dict[str, Any]:
    """响应节点：生成回复

    基于对话和工具结果生成最终响应
    """
    # TODO: 实现真实响应生成
    return {
        "current_step": "responding",
        "messages": [{"role": "assistant", "content": "Response placeholder"}],
    }


async def human_node(state: AgentState) -> Dict[str, Any]:
    """人工介入节点：等待用户输入

    此节点可以中断，等待用户确认或输入
    """
    return {
        "current_step": "human",
    }


async def error_node(state: AgentState) -> Dict[str, Any]:
    """错误处理节点"""
    return {
        "current_step": "error",
    }


def route_from_think(state: AgentState) -> str:
    """从思考节点路由

    决定下一步是调用工具、直接响应还是需要人工介入
    """
    if state.get("error"):
        return "error"

    if state.get("tool_calls"):
        return "call_tools"

    # 需要人工确认的场景
    if state.get("context", {}).get("requires_human"):
        return "human"

    return "respond"


def create_agent_graph(
    interrupt_before: Optional[List[str]] = None,
) -> StateGraph:
    """创建 Agent 对话状态图

    Args:
        interrupt_before: 中断点节点列表（如 ["human"]）

    Returns:
        StateGraph: Agent 状态图实例
    """
    # 创建状态图
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("think", think_node)
    graph.add_node("call_tools", call_tools_node)
    graph.add_node("respond", respond_node)
    graph.add_node("human", human_node)
    graph.add_node("error", error_node)

    # 设置入口
    graph.set_entry_point("think")

    # 添加边
    graph.add_conditional_edges("think", route_from_think)
    graph.add_edge("call_tools", "think")  # 工具调用后继续思考
    graph.add_edge("respond", END)
    graph.add_edge("human", "think")  # 人工输入后继续思考
    graph.add_edge("error", END)

    return graph


async def run_agent_conversation(
    thread_id: str,
    user_id: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    checkpointer: Optional[PostgresSaver] = None,
) -> Dict[str, Any]:
    """运行 Agent 对话

    Args:
        thread_id: 会话线程 ID
        user_id: 用户 ID
        message: 用户消息
        context: 执行上下文
        checkpointer: Checkpointer 实例

    Returns:
        Agent 执行结果
    """
    from app.graphs.checkpointer import get_checkpointer

    if checkpointer is None:
        checkpointer = get_checkpointer()

    graph = create_agent_graph()
    compiled = graph.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": thread_id}}

    initial_state = AgentState(
        thread_id=thread_id,
        user_id=user_id,
        messages=[{"role": "user", "content": message}],
        current_step="idle",
        tool_calls=[],
        tool_results=[],
        context=context or {},
        error=None,
    )

    result = await compiled.invoke(initial_state, config)
    return result


async def resume_agent_conversation(
    thread_id: str,
    user_input: str,
    checkpointer: Optional[PostgresSaver] = None,
) -> Dict[str, Any]:
    """恢复 Agent 对话

    从中断点恢复，继续执行

    Args:
        thread_id: 会话线程 ID
        user_input: 用户输入
        checkpointer: Checkpointer 实例

    Returns:
        Agent 执行结果
    """
    from app.graphs.checkpointer import get_checkpointer

    if checkpointer is None:
        checkpointer = get_checkpointer()

    graph = create_agent_graph()
    compiled = graph.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": thread_id}}

    # 获取当前状态
    current = await compiled.get_state(config)

    # 更新状态
    await compiled.update_state(
        config,
        {
            "messages": [{"role": "user", "content": user_input}],
            "current_step": "idle",
        }
    )

    # 继续执行
    result = await compiled.invoke(None, config)
    return result