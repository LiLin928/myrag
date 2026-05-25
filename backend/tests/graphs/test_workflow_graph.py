# backend/tests/graphs/test_workflow_graph.py

import pytest
from app.graphs.workflow_graph import WorkflowState, create_workflow_graph


def test_workflow_state_definition():
    """测试 WorkflowState 类型定义"""
    state = WorkflowState(
        workflow_id="wf-001",
        execution_id="exec-001",
        user_id="user-001",
        variables={},
        node_outputs={},
        current_node=None,
        status="pending",
        error=None,
        started_at="2024-01-01T00:00:00",
        completed_at=None,
    )
    assert state["workflow_id"] == "wf-001"
    assert state["status"] == "pending"


def test_workflow_graph_creation():
    """测试工作流状态图创建"""
    graph = create_workflow_graph()
    assert graph is not None

    compiled = graph.compile()
    assert compiled is not None


def test_workflow_graph_nodes():
    """测试工作流状态图节点"""
    graph = create_workflow_graph()

    # 验证节点存在
    nodes = graph.nodes
    assert "execute" in nodes
    assert "error_handler" in nodes


@pytest.mark.skipif(
    True,  # 默认跳过，需要真实数据库时设置为 False
    reason="需要真实 PostgreSQL 数据库连接"
)
@pytest.mark.asyncio
async def test_workflow_graph_basic_execution():
    """测试工作流基本执行流程（需要真实数据库）"""
    from app.graphs.checkpointer import get_checkpointer

    graph = create_workflow_graph()
    compiled = graph.compile(checkpointer=get_checkpointer())

    thread_id = "wf-test-001"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = WorkflowState(
        workflow_id="wf-001",
        execution_id="exec-001",
        user_id="user-001",
        variables={"input": "test"},
        node_outputs={},
        current_node="start",
        status="pending",
        error=None,
        started_at="2024-01-01T00:00:00",
        completed_at=None,
    )

    result = await compiled.invoke(initial_state, config)
    assert result is not None


@pytest.mark.skipif(
    True,  # 默认跳过，需要真实数据库时设置为 False
    reason="需要真实 PostgreSQL 数据库连接"
)
@pytest.mark.asyncio
async def test_workflow_graph_interrupt_resume():
    """测试工作流中断恢复（需要真实数据库）"""
    from app.graphs.checkpointer import get_checkpointer

    graph = create_workflow_graph(interrupt_before=["human_node"])
    compiled = graph.compile(checkpointer=get_checkpointer())

    thread_id = "wf-test-002"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = WorkflowState(
        workflow_id="wf-002",
        execution_id="exec-002",
        user_id="user-001",
        variables={"input": "test"},
        node_outputs={},
        current_node="start",
        status="pending",
        error=None,
        started_at="2024-01-01T00:00:00",
        completed_at=None,
    )

    # 执行到中断点
    result = await compiled.invoke(initial_state, config)

    # 获取当前状态
    current = await compiled.get_state(config)
    assert current is not None

    # 恢复执行
    result = await compiled.invoke(None, config)
    assert result is not None