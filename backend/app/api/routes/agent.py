# app/api/routes/agent.py

"""Agent API 路由

提供 Agent 对话相关 API：
- chat: 执行对话
- resume: 中断恢复
- history: 对话历史
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.agent_service import agent_service
from app.api.dependencies.auth import get_current_user
from app.models.user import User


router = APIRouter(prefix="/agent", tags=["agent"])


class ChatRequest(BaseModel):
    """对话请求"""
    thread_id: str
    message: str
    user_id: str
    system_prompt: Optional[str] = None


class ChatResponse(BaseModel):
    """对话响应"""
    thread_id: str
    response: str
    messages: list


class ResumeRequest(BaseModel):
    """中断恢复请求"""
    thread_id: str
    decision: str  # "approve", "reject", "edit"
    edited_args: Optional[dict] = None


class ResumeResponse(BaseModel):
    """中断恢复响应"""
    thread_id: str
    decision: str
    response: str


class HistoryResponse(BaseModel):
    """对话历史响应"""
    thread_id: str
    messages: list


class InterruptResponse(BaseModel):
    """中断信息响应"""
    thread_id: str
    task: Optional[dict] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """执行对话

    Args:
        request: 对话请求

    Returns:
        对话响应
    """
    try:
        result = await agent_service.chat(
            thread_id=request.thread_id,
            message=request.message,
            user_id=request.user_id,
            system_prompt=request.system_prompt,
        )
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume", response_model=ResumeResponse)
async def resume(
    request: ResumeRequest,
    current_user: User = Depends(get_current_user),
):
    """从中断点恢复

    用于 Human-in-the-Loop 场景。

    Args:
        request: 恢复请求

    Returns:
        恢复后的响应
    """
    if request.decision not in ["approve", "reject", "edit"]:
        raise HTTPException(status_code=400, detail="Invalid decision")

    try:
        result = await agent_service.resume_from_interrupt(
            thread_id=request.thread_id,
            decision=request.decision,
            edited_args=request.edited_args,
        )
        return ResumeResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{thread_id}", response_model=HistoryResponse)
async def get_history(
    thread_id: str,
    current_user: User = Depends(get_current_user),
):
    """获取对话历史

    Args:
        thread_id: 会话线程 ID

    Returns:
        对话历史
    """
    try:
        messages = await agent_service.get_conversation_history(thread_id)
        return HistoryResponse(thread_id=thread_id, messages=messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interrupt/{thread_id}", response_model=InterruptResponse)
async def get_interrupt(
    thread_id: str,
    current_user: User = Depends(get_current_user),
):
    """获取待处理的中断

    Args:
        thread_id: 会话线程 ID

    Returns:
        中断信息
    """
    try:
        result = await agent_service.get_pending_interrupt(thread_id)
        if result:
            return InterruptResponse(**result)
        return InterruptResponse(thread_id=thread_id, task=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))