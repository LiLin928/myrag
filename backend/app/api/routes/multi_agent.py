# app/api/routes/multi_agent.py
"""多 Agent API 路由"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.multi_agent_service import MultiAgentService


router = APIRouter(prefix="/multi-agent", tags=["Multi-Agent"])


class ProcessTaskRequest(BaseModel):
    """任务处理请求"""

    task_description: str
    context: Optional[Dict[str, Any]] = None


class DispatchRequest(BaseModel):
    """分发请求"""

    agent_name: str
    task: str
    context: Optional[Dict[str, Any]] = None


class TaskResponse(BaseModel):
    """任务响应"""

    result: str
    agent_used: Optional[str] = None


class AgentStatusResponse(BaseModel):
    """Agent 状态响应"""

    total: int
    agents: Dict[str, Any]


def get_multi_agent_service() -> MultiAgentService:
    """获取多 Agent 服务实例"""
    return MultiAgentService()


@router.post("/process", response_model=TaskResponse)
async def process_task(
    request: ProcessTaskRequest,
    service: MultiAgentService = Depends(get_multi_agent_service)
):
    """处理任务 - 通过 Master Agent 自动分发

    Args:
        request: 任务处理请求
        service: 多 Agent 服务

    Returns:
        处理结果
    """
    try:
        result = await service.process_task(
            request.task_description,
            request.context
        )
        return TaskResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dispatch", response_model=TaskResponse)
async def dispatch_to_agent(
    request: DispatchRequest,
    service: MultiAgentService = Depends(get_multi_agent_service)
):
    """直接分发到特定 Agent

    Args:
        request: 分发请求
        service: 多 Agent 服务

    Returns:
        处理结果
    """
    try:
        result = await service.dispatch_to_agent(
            request.agent_name,
            request.task,
            request.context
        )
        return TaskResponse(result=result, agent_used=request.agent_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=AgentStatusResponse)
async def get_agent_status(
    service: MultiAgentService = Depends(get_multi_agent_service)
):
    """获取所有 Agent 状态

    Returns:
        Agent 状态信息
    """
    return service.get_agent_status()


@router.get("/agents")
async def get_available_agents(
    service: MultiAgentService = Depends(get_multi_agent_service)
):
    """获取可用 Agent 列表

    Returns:
        Agent 名称列表
    """
    return {"agents": service.get_available_agents()}