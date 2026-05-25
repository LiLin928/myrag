# backend/tests/graphs/test_agent_graph.py

import pytest
from app.graphs.agent_graph import AgentState, create_agent_graph


def test_agent_state_definition():
    """测试 AgentState 类型定义"""
    # 验证 TypedDict 字段
    state = AgentState(
        thread_id="test-001",
        user_id="user-001",
        messages=[],
        current_step="idle",
        tool_calls=[],
        tool_results=[],
        context={},
        error=None,
    )
    assert state["thread_id"] == "test-001"
    assert state["current_step"] == "idle"


def test_agent_graph_creation():
    """测试 Agent 状态图创建"""
    graph = create_agent_graph()
    assert graph is not None

    # 验证编译后的图
    compiled = graph.compile()
    assert compiled is not None


def test_agent_graph_nodes():
    """测试 Agent 状态图节点"""
    graph = create_agent_graph()

    # 验证节点存在
    nodes = graph.nodes
    assert "think" in nodes
    assert "call_tools" in nodes
    assert "respond" in nodes
    assert "human" in nodes
    assert "error" in nodes


@pytest.mark.skipif(
    True,  # 默认跳过，需要真实数据库时设置为 False
    reason="需要真实 PostgreSQL 数据库连接"
)
@pytest.mark.asyncio
async def test_agent_graph_invoke():
    """测试 Agent 状态图执行（需要真实数据库）"""
    from app.graphs.checkpointer import get_checkpointer

    graph = create_agent_graph()
    compiled = graph.compile(checkpointer=get_checkpointer())

    thread_id = "test-thread-001"
    config = {"configurable": {"thread_id": thread_id}}

    # 初始状态
    initial_state = AgentState(
        thread_id=thread_id,
        user_id="user-001",
        messages=[{"role": "user", "content": "Hello"}],
        current_step="idle",
        tool_calls=[],
        tool_results=[],
        context={},
        error=None,
    )

    # 执行
    result = await compiled.invoke(initial_state, config)
    assert result is not None


@pytest.mark.skipif(
    True,  # 默认跳过，需要真实数据库时设置为 False
    reason="需要真实 PostgreSQL 数据库连接"
)
@pytest.mark.asyncio
async def test_agent_graph_interrupt_resume():
    """测试 Agent 状态图中断恢复（需要真实数据库）"""
    from app.graphs.checkpointer import get_checkpointer

    graph = create_agent_graph(interrupt_before=["human"])
    compiled = graph.compile(checkpointer=get_checkpointer())

    thread_id = "test-thread-002"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = AgentState(
        thread_id=thread_id,
        user_id="user-001",
        messages=[{"role": "user", "content": "Process this"}],
        current_step="idle",
        tool_calls=[],
        tool_results=[],
        context={},
        error=None,
    )

    # 执行到中断点
    result = await compiled.invoke(initial_state, config)
    # 应该在 human node 前中断

    # 获取当前状态
    current = await compiled.get_state(config)
    assert current is not None