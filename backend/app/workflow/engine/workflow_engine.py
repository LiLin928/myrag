"""工作流执行引擎

使用 LangGraph StateGraph 执行工作流定义
"""

from typing import Dict, Any, List, TypedDict, Optional
from langgraph.graph import StateGraph, END
import uuid
import logging

from app.workflow.engine.node_router import create_node
from app.graphs.checkpointer import get_checkpointer
from app.workflow.workflow_progress_tracker import WorkflowProgressTracker
from app.workflow.variable_resolver import VariableResolver
from app.workflow.langfuse_tracker import (
    get_langfuse_client,
    create_trace_context,
    create_trace,
    update_trace,
    end_trace,
    end_observation,
    flush_client,
    get_langchain_handler,
)
from app.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """工作流执行状态"""
    workflow_id: str
    execution_id: str
    thread_id: str
    user_id: str

    # 执行上下文
    variables: Dict[str, Any]
    node_outputs: Dict[str, Dict[str, Any]]
    current_node: str

    # 状态追踪
    status: str
    error: str | None

    # 人工介入
    human_prompt: str | None
    human_input: str | None


class WorkflowEngine:
    """工作流执行引擎"""

    async def build_graph(
        self,
        workflow_definition: Dict[str, Any],
        resolver: VariableResolver,
        progress_tracker: Optional[WorkflowProgressTracker] = None,
        db: AsyncSession = None,
    ) -> StateGraph:
        """构建工作流状态图

        Args:
            workflow_definition: 工作流定义（nodes, edges）
            resolver: 变量解析器
            progress_tracker: 进度追踪器（可选）
            db: 数据库会话（用于节点查询模型配置）

        Returns:
            StateGraph
        """
        nodes = workflow_definition.get("nodes", [])
        edges = workflow_definition.get("edges", [])

        graph = StateGraph(WorkflowState)

        # 添加节点
        for node_def in nodes:
            node_id = node_def["id"]
            node_type = node_def["type"]
            # 配置直接在 data 下面，不是 data.config
            node_config = node_def.get("data", {})

            # 重要：不在构建图时解析变量引用，因为此时 node_outputs 还没有数据
            # 节点配置中的 ${node_id.output} 等引用应该在节点执行时解析
            # 只保留原始配置，不做解析
            resolved_config = node_config.copy() if node_config else {}

            # 确保 input_variables 未被修改
            if node_config and "input_variables" in node_config:
                resolved_config["input_variables"] = node_config["input_variables"]

            logger.warning(f"WorkflowEngine: node {node_id} type={node_type}, FULL CONFIG: {resolved_config}")  # WARNING 级别确保显示

            # 创建节点处理器闭包（传递 db 用于节点查询配置）
            async def make_handler(nid, ntype, nconfig, tracker, var_resolver, db_session):
                async def node_handler(state: WorkflowState) -> Dict[str, Any]:
                    # 将 db 注入到状态中（不序列化）
                    state_with_db = {**state, "_db": db_session}

                    # 节点开始执行
                    if tracker:
                        await tracker.on_node_start(nid, {"variables": state.get("variables")})

                    node = create_node(nid, ntype, nconfig)
                    result = await node.execute(state_with_db)

                    # 更新状态
                    updates = {
                        "current_node": nid,
                        "node_outputs": {
                            **state.get("node_outputs", {}),
                            nid: result.output,
                        },
                    }

                    if result.error:
                        updates["error"] = result.error
                        updates["status"] = "failed"
                        # 节点执行错误
                        if tracker:
                            await tracker.on_node_error(nid, result.error)
                    else:
                        # 将节点输出添加到 resolver
                        var_resolver.add_node_output(nid, result.output)
                        # 节点执行完成
                        if tracker:
                            await tracker.on_node_complete(nid, result.output)

                    # 条件节点返回 next_node
                    if result.next_node:
                        updates["_next_node"] = result.next_node

                    return updates
                return node_handler

            graph.add_node(node_id, await make_handler(node_id, node_type, resolved_config, progress_tracker, resolver, db))

        # 添加边
        # 首先找到 start 类型的节点作为入口点
        start_node_id = None
        for node_def in nodes:
            if node_def.get("type") == "start":
                start_node_id = node_def["id"]
                break

        for edge_def in edges:
            source = edge_def["source"]
            target = edge_def["target"]
            label = edge_def.get("label")

            # 使用节点类型判断入口点，而不是固定 ID
            if source == start_node_id or source == "start":
                graph.set_entry_point(target)
            elif target == "end" or (target.endswith("-end") or target.startswith("end")):
                # 检查目标是否是结束节点
                # 找到目标节点的类型
                target_node_type = None
                for node_def in nodes:
                    if node_def["id"] == target:
                        target_node_type = node_def.get("type")
                        break
                if target_node_type == "end":
                    graph.add_edge(source, END)
                else:
                    graph.add_edge(source, target)
            elif label:
                # 条件边
                def route(state: WorkflowState) -> str:
                    next_node = state.get("_next_node")
                    return next_node if next_node else target

                graph.add_conditional_edges(source, route)
            else:
                graph.add_edge(source, target)

        return graph

    async def execute(
        self,
        workflow_id: str,
        execution_id: str,
        workflow_definition: Dict[str, Any],
        initial_variables: Dict[str, Any],
        user_id: str,
        interrupt_before: List[str] = None,
        db: AsyncSession = None,
    ) -> Dict[str, Any]:
        """执行工作流

        Args:
            workflow_id: 工作流 ID
            execution_id: 执行 ID
            workflow_definition: 工作流定义
            initial_variables: 初始变量
            user_id: 用户 ID
            interrupt_before: 中断点节点列表
            db: 数据库会话（可选，用于进度追踪）

        Returns:
            执行结果
        """
        # 创建进度追踪器
        progress_tracker = None
        if db:
            nodes = workflow_definition.get("nodes", [])
            # 构建节点名称和类型映射
            node_names = {}
            node_types = {}
            for node_def in nodes:
                node_id = node_def["id"]
                node_names[node_id] = node_def.get("data", {}).get("label", node_id)
                node_types[node_id] = node_def.get("type")

            progress_tracker = WorkflowProgressTracker(
                execution_id=execution_id,
                workflow_id=workflow_id,
                user_id=user_id,
                db=db,
                node_names=node_names,
                node_types=node_types,
            )

            # 执行开始
            await progress_tracker.on_execution_start(len(nodes))

        # 创建 Langfuse Trace（如果启用）
        settings = get_settings()
        trace = None
        if settings.langfuse_available:
            try:
                # 提取工作流名称
                workflow_name = "Unknown"
                for node_def in workflow_definition.get("nodes", []):
                    if node_def.get("type") == "start":
                        workflow_name = node_def.get("data", {}).get("label", "Unknown")
                        break

                trace = create_trace(
                    trace_id=execution_id,
                    name=f"Workflow: {workflow_name}",
                    user_id=user_id,
                    session_id=f"wf_{workflow_id}_exec_{execution_id}",
                    metadata={
                        "workflow_id": workflow_id,
                        "total_nodes": len(workflow_definition.get("nodes", [])),
                    },
                )
                if trace:
                    logger.info(f"Langfuse trace created: {execution_id}")
            except Exception as e:
                logger.warning(f"Langfuse trace creation failed: {e}")

        # 创建变量解析器
        resolver = VariableResolver(input_vars=initial_variables)

        # 构建状态图，传入 resolver 和 db
        graph = await self.build_graph(workflow_definition, resolver, progress_tracker, db)

        # 确保连接池已打开（避免连接中断错误）
        from app.graphs.checkpointer import ensure_pool_open
        await ensure_pool_open()

        # 编译
        checkpointer = get_checkpointer()
        compiled = graph.compile(
            checkpointer=checkpointer,
            interrupt_before=interrupt_before or [],
        )

        # 初始状态
        thread_id = f"wf_{workflow_id}_exec_{execution_id}"
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = WorkflowState(
            workflow_id=workflow_id,
            execution_id=execution_id,
            thread_id=thread_id,
            user_id=user_id,
            variables=initial_variables,
            node_outputs={},
            current_node="start",
            status="running",
            error=None,
            human_prompt=None,
            human_input=None,
        )

        # 执行（使用 ainvoke 确保异步节点正确执行）
        try:
            result = await compiled.ainvoke(initial_state, config)
            logger.info(f"Workflow execution completed: {result}")
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            result = {
                "status": "failed",
                "error": str(e),
                "current_node": None,
                "node_outputs": {},
            }

        # 执行完成或中断
        if progress_tracker:
            if result.get("status") == "failed":
                # 错误已在节点处理器中记录
                pass
            elif interrupt_before and result.get("current_node") in (interrupt_before or []):
                # 执行中断（人工节点等待）
                await progress_tracker.on_execution_interrupted(
                    result.get("current_node"),
                    "Waiting for human input"
                )
            else:
                # 执行完成
                await progress_tracker.on_execution_complete(result.get("node_outputs"))

        # 更新 Langfuse Trace 状态
        if trace:
            try:
                if result.get("status") == "failed":
                    end_trace(
                        trace,
                        metadata={
                            "status": "error",
                            "error": result.get("error"),
                            "error_node": result.get("current_node"),
                        },
                    )
                else:
                    end_trace(
                        trace,
                        metadata={"status": "success"},
                        output=result.get("node_outputs"),
                    )
                # 刷新确保数据写入
                flush_client()
            except Exception as e:
                logger.warning(f"Langfuse trace end failed: {e}")

        return result

    async def resume(
        self,
        thread_id: str,
        workflow_definition: Dict[str, Any],
        user_input: str,
        initial_variables: Dict[str, Any] = None,
        progress_tracker: Optional[WorkflowProgressTracker] = None,
        db: AsyncSession = None,
    ) -> Dict[str, Any]:
        """恢复工作流

        Args:
            thread_id: LangGraph thread ID
            workflow_definition: 工作流定义
            user_input: 用户输入
            initial_variables: 初始变量
            progress_tracker: 进度追踪器（可选）
            db: 数据库会话（用于节点查询模型配置）

        Returns:
            执行结果
        """
        # 创建变量解析器
        resolver = VariableResolver(input_vars=initial_variables or {})

        # 构建状态图
        graph = await self.build_graph(workflow_definition, resolver, progress_tracker, db)

        # 编译
        checkpointer = get_checkpointer()
        compiled = graph.compile(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": thread_id}}

        # 获取当前状态
        current = await compiled.get_state(config)

        # 更新状态
        await compiled.update_state(
            config,
            {
                "human_input": user_input,
                "status": "running",
            }
        )

        # 继续执行（使用 ainvoke 确保异步节点正确执行）
        result = await compiled.ainvoke(None, config)

        # 执行完成
        if progress_tracker:
            if result.get("status") == "failed":
                # 错误已在节点处理器中记录
                pass
            else:
                # 执行完成
                await progress_tracker.on_execution_complete(result.get("node_outputs"))

        return result


# 全局引擎实例
workflow_engine = WorkflowEngine()