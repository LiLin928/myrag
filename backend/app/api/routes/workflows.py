"""工作流 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Dict, Any, Optional
from datetime import datetime as dt
from pydantic import BaseModel
import uuid

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.workflow.models.workflow import Workflow
from app.workflow.models.execution import WorkflowExecution
from app.workflow.engine.workflow_engine import workflow_engine
from app.db import get_db

router = APIRouter(prefix="/workflows", tags=["workflows"])


class WorkflowUpdateRequest(BaseModel):
    """更新工作流请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    definition: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


@router.post("/")
async def create_workflow(
    name: str = Body(...),
    description: str = Body(None),
    definition: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建工作流

    Args:
        name: 工作流名称
        description: 描述
        definition: 工作流定义（nodes, edges）

    Returns:
        工作流信息
    """
    workflow = Workflow(
        name=name,
        description=description,
        definition=definition,
        user_id=current_user.id,
        status="draft",  # 使用字符串值
    )

    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)

    return {
        "id": str(workflow.id),
        "name": workflow.name,
        "description": workflow.description,
        "definition": workflow.definition,
        "status": workflow.status,  # 直接返回字符串
        "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
    }


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取工作流详情"""
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {
        "id": str(workflow.id),
        "name": workflow.name,
        "description": workflow.description,
        "status": workflow.status,
        "definition": workflow.definition,
        "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
        "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
    }


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    data: WorkflowUpdateRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新工作流"""
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if workflow.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this workflow")

    if data.name is not None:
        workflow.name = data.name
    if data.description is not None:
        workflow.description = data.description
    if data.definition is not None:
        workflow.definition = data.definition
    if data.status is not None:
        # 验证状态值是否有效
        valid_statuses = ["draft", "published", "archived"]
        if data.status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Valid values: {valid_statuses}")
        workflow.status = data.status

    workflow.updated_at = dt.utcnow()
    await db.commit()
    await db.refresh(workflow)

    return {
        "id": str(workflow.id),
        "name": workflow.name,
        "description": workflow.description,
        "status": workflow.status,
        "definition": workflow.definition,
    }


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除工作流"""
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if workflow.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this workflow")

    await db.delete(workflow)
    await db.commit()

    return {"deleted": workflow_id}


@router.get("/")
async def list_workflows(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出工作流"""
    result = await db.execute(
        select(Workflow).where(Workflow.user_id == current_user.id)
    )
    workflows = result.scalars().all()

    return [
        {
            "id": str(w.id),
            "name": w.name,
            "description": w.description,
            "status": w.status,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        }
        for w in workflows
    ]


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    initial_variables: Dict[str, Any] = Body(default={}),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """执行工作流

    Args:
        workflow_id: 工作流 ID
        initial_variables: 初始变量

    Returns:
        执行信息
    """
    # 获取工作流
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # 创建执行记录
    thread_id = str(uuid.uuid4())

    execution = WorkflowExecution(
        workflow_id=workflow.id,
        user_id=current_user.id,
        status="pending",
        thread_id=thread_id,
        variables=initial_variables,
    )

    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # 执行工作流
    try:
        # 获取人工介入节点列表
        human_nodes = [
            node["id"]
            for node in workflow.definition.get("nodes", [])
            if node["type"] == "human"
        ]

        result = await workflow_engine.execute(
            workflow_id=workflow_id,
            execution_id=str(execution.id),
            workflow_definition=workflow.definition,
            initial_variables=initial_variables,
            user_id=str(current_user.id),
            interrupt_before=human_nodes,
            db=db,  # Pass db session for progress tracking
        )

        # 更新执行状态
        if result.get("error"):
            execution.status = "failed"
            execution.error_message = result.get("error")
        else:
            execution.status = "running"

        execution.current_node = result.get("current_node")
        execution.node_outputs = result.get("node_outputs")
        execution.started_at = dt.utcnow()

        await db.commit()

        return {
            "execution_id": str(execution.id),
            "thread_id": thread_id,
            "status": execution.status,
            "error": result.get("error"),
            "node_outputs": result.get("node_outputs"),
            "current_node": result.get("current_node"),
        }

    except Exception as e:
        execution.status = "failed"
        execution.error_message = str(e)
        await db.commit()

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/executions/{execution_id}/resume")
async def resume_workflow(
    execution_id: str,
    user_input: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """恢复工作流执行

    Args:
        execution_id: 执行 ID
        user_input: 用户输入

    Returns:
        执行结果
    """
    # 获取执行记录
    result = await db.execute(
        select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    # 获取工作流
    wf_result = await db.execute(
        select(Workflow).where(Workflow.id == execution.workflow_id)
    )
    workflow = wf_result.scalar_one_or_none()

    # 恢复执行
    try:
        result = await workflow_engine.resume(
            thread_id=execution.thread_id,
            workflow_definition=workflow.definition,
            user_input=user_input,
        )

        # 更新执行状态
        execution.status = "completed"
        execution.human_input = user_input
        execution.completed_at = dt.utcnow()

        await db.commit()

        return {
            "execution_id": execution_id,
            "status": execution.status,
            "result": result,
        }

    except Exception as e:
        execution.status = "failed"
        execution.error_message = str(e)
        await db.commit()

        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取执行详情"""
    result = await db.execute(
        select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return {
        "id": str(execution.id),
        "workflow_id": str(execution.workflow_id),
        "status": execution.status,
        "thread_id": execution.thread_id,
        "current_node": execution.current_node,
        "node_outputs": execution.node_outputs,
        "started_at": execution.started_at,
        "completed_at": execution.completed_at,
    }


@router.get("/executions")
async def list_executions(
    workflow_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取执行历史列表"""
    conditions = [WorkflowExecution.user_id == current_user.id]

    if workflow_id:
        try:
            conditions.append(WorkflowExecution.workflow_id == workflow_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid workflow_id format")

    if status:
        # 验证状态值是否有效
        valid_statuses = ["pending", "running", "paused", "completed", "failed", "cancelled"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status value. Valid values: {valid_statuses}")
        conditions.append(WorkflowExecution.status == status)

    if start_date:
        try:
            conditions.append(WorkflowExecution.started_at >= dt.fromisoformat(start_date))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO format (e.g., 2024-01-01T00:00:00)")

    if end_date:
        try:
            conditions.append(WorkflowExecution.started_at <= dt.fromisoformat(end_date))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use ISO format (e.g., 2024-01-01T23:59:59)")

    # 查询总数
    count_query = select(func.count()).select_from(WorkflowExecution).where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页查询
    offset = (page - 1) * page_size
    query = select(WorkflowExecution, Workflow.name).join(
        Workflow, WorkflowExecution.workflow_id == Workflow.id
    ).where(and_(*conditions)).order_by(
        WorkflowExecution.created_at.desc()
    ).offset(offset).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    # 计算耗时
    items = []
    for execution, workflow_name in rows:
        duration_ms = None
        if execution.started_at and execution.completed_at:
            duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)

        items.append({
            "id": str(execution.id),
            "workflow_id": str(execution.workflow_id),
            "workflow_name": workflow_name,
            "status": execution.status,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "duration_ms": duration_ms,
            "triggered_by": current_user.username,
            "error_summary": execution.error_message[:100] if execution.error_message else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.delete("/executions/{execution_id}")
async def delete_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除执行记录"""
    result = await db.execute(
        select(WorkflowExecution).where(
            and_(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.user_id == current_user.id,
            )
        )
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    await db.delete(execution)
    await db.commit()

    return {"message": "Execution deleted"}


@router.post("/executions/{execution_id}/rerun")
async def rerun_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重新执行工作流（使用相同输入参数）"""
    result = await db.execute(
        select(WorkflowExecution).where(
            and_(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.user_id == current_user.id,
            )
        )
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    # 获取工作流
    wf_result = await db.execute(
        select(Workflow).where(Workflow.id == execution.workflow_id)
    )
    workflow = wf_result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # 创建新执行记录
    new_thread_id = str(uuid.uuid4())
    new_execution = WorkflowExecution(
        workflow_id=workflow.id,
        user_id=current_user.id,
        status="pending",
        thread_id=new_thread_id,
        variables=execution.variables,  # 使用原执行的输入变量
    )

    db.add(new_execution)
    await db.commit()
    await db.refresh(new_execution)

    return {
        "execution_id": str(new_execution.id),
        "message": "Execution created",
    }