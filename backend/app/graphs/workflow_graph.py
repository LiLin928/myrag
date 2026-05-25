"""工作流执行状态机

实现工作流执行的 LangGraph StateGraph，支持：
- 多节点执行（LLM、RAG、Code、HTTP 等）
- 条件分支和循环
- 人工介入（中断恢复）
"""

from typing import TypedDict, Dict, Any, Literal, Optional, List
from langgraph.graph import StateGraph, END
from datetime import datetime


class WorkflowState(TypedDict):
    """工作流执行状态定义

    Attributes:
        workflow_id: 工作流定义 ID
        execution_id: 执行实例 ID
        user_id: 执行用户 ID
        variables: 工作流变量
        node_outputs: 各节点输出结果
        current_node: 当前执行节点
        status: 执行状态
        error: 错误信息
        started_at: 开始时间
        completed_at: 完成时间
    """
    workflow_id: str
    execution_id: str
    user_id: str
    variables: Dict[str, Any]
    node_outputs: Dict[str, Dict[str, Any]]
    current_node: Optional[str]
    status: Literal["pending", "running", "paused", "completed", "failed"]
    error: Optional[str]
    started_at: str
    completed_at: Optional[str]


# 节点处理器（骨架）

async def execute_node(state: WorkflowState) -> Dict[str, Any]:
    """执行当前节点

    根据 current_node 类型调用对应处理器
    """
    node_type = state.get("current_node")

    if node_type == "start":
        return {"status": "running", "current_node": None}

    if node_type == "end":
        return {
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
        }

    # TODO: 实现真实节点执行逻辑
    # 根据节点类型调用：
    # - LLM 节点：调用 LLM
    # - RAG 节点：执行检索
    # - Code 节点：执行代码
    # - HTTP 节点：发送请求
    # - Condition 节点：条件分支
    # - Human 节点：等待人工输入

    return {"node_outputs": state["node_outputs"]}


async def error_handler_node(state: WorkflowState) -> Dict[str, Any]:
    """错误处理节点"""
    return {
        "status": "failed",
        "completed_at": datetime.now().isoformat(),
    }


def route_next_node(state: WorkflowState) -> str:
    """路由到下一节点

    根据工作流定义决定下一个节点
    """
    if state.get("error"):
        return "error_handler"

    if state["status"] == "completed":
        return END

    # TODO: 实现真实路由逻辑
    # 从工作流定义中获取下一节点
    # 根据条件分支决定路由

    return "execute"


def create_workflow_graph(
    interrupt_before: Optional[List[str]] = None,
) -> StateGraph:
    """创建工作流执行状态图

    Args:
        interrupt_before: 中断点节点列表（如 ["human_node"]）

    Returns:
        StateGraph: 工作流状态图实例
    """
    graph = StateGraph(WorkflowState)

    # 添加节点
    graph.add_node("execute", execute_node)
    graph.add_node("error_handler", error_handler_node)

    # 设置入口
    graph.set_entry_point("execute")

    # 添加边
    graph.add_conditional_edges("execute", route_next_node)
    graph.add_edge("error_handler", END)

    return graph


async def run_workflow(
    workflow_id: str,
    user_id: str,
    variables: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """运行工作流

    Args:
        workflow_id: 工作流定义 ID
        user_id: 用户 ID
        variables: 输入变量

    Returns:
        工作流执行结果
    """
    from app.graphs.checkpointer import get_checkpointer

    checkpointer = get_checkpointer()
    graph = create_workflow_graph()
    compiled = graph.compile(checkpointer=checkpointer)

    execution_id = f"exec-{workflow_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    thread_id = execution_id
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = WorkflowState(
        workflow_id=workflow_id,
        execution_id=execution_id,
        user_id=user_id,
        variables=variables or {},
        node_outputs={},
        current_node="start",
        status="pending",
        error=None,
        started_at=datetime.now().isoformat(),
        completed_at=None,
    )

    result = await compiled.invoke(initial_state, config)
    return result


async def resume_workflow(
    execution_id: str,
    user_input: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """恢复工作流执行

    从中断点恢复，继续执行

    Args:
        execution_id: 执行实例 ID
        user_input: 用户输入（更新变量）

    Returns:
        工作流执行结果
    """
    from app.graphs.checkpointer import get_checkpointer

    checkpointer = get_checkpointer()
    graph = create_workflow_graph()
    compiled = graph.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": execution_id}}

    # 获取当前状态
    current = await compiled.get_state(config)

    # 更新状态
    update = {
        "status": "running",
    }
    if user_input:
        update["variables"] = {**current.values["variables"], **user_input}

    await compiled.update_state(config, update)

    # 继续执行
    result = await compiled.invoke(None, config)
    return result