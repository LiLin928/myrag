"""Agent 公开访问 API 路由（无需认证）"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import uuid
import datetime

from app.db import get_db
from app.models.agent import Agent
from app.models.agent_publish import AgentPublish
from app.schemas.agent_publish import PublicChatRequest
from app.schemas.agent_chat import ChatResponse, SourceReference
from app.services.agent_engine import AgentEngine

router = APIRouter(prefix="/public", tags=["public"])


@router.post("/agents/{publish_id}/chat", response_model=ChatResponse)
async def public_chat(
    publish_id: str,
    data: PublicChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """公开对话入口"""
    try:
        pid = uuid.UUID(publish_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid publish_id format")

    # 获取发布记录
    result = await db.execute(
        select(AgentPublish)
        .where(and_(AgentPublish.id == pid, AgentPublish.status == "active"))
    )
    publish = result.scalar_one_or_none()

    if not publish:
        raise HTTPException(status_code=404, detail="Publish not found or disabled")

    # 获取 Agent
    agent_result = await db.execute(
        select(Agent)
        .where(Agent.id == publish.agent_id)
        .options(selectinload(Agent.knowledge_bindings))
    )
    agent = agent_result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 执行对话
    engine = AgentEngine(agent, agent.knowledge_bindings)
    chat_result = await engine.chat(data.message, data.thread_id)

    # 更新访问统计
    publish.access_count += 1
    await db.commit()

    return ChatResponse(
        session_id=data.thread_id or str(uuid.uuid4()),
        response=chat_result["response"],
        sources=[SourceReference(**s) for s in chat_result.get("sources", [])],
        tool_calls=[],
        created_at=datetime.datetime.utcnow(),
    )


@router.get("/embed/{publish_id}/", response_class=HTMLResponse)
async def get_embed_page(publish_id: str):
    """嵌入页面"""
    return '''<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>MyRAG Agent</title>
  <style>
    body { margin: 0; font-family: sans-serif; }
    .chat-container {
      width: 100%; height: 100vh;
      display: flex; flex-direction: column;
      background: #f5f5f5;
    }
    .messages { flex: 1; padding: 16px; overflow-y: auto; }
    .input-area { padding: 16px; background: white; }
    .input { width: 100%; padding: 8px; border: 1px solid #ddd; }
    .send-btn { margin-top: 8px; }
  </style>
</head>
<body>
  <div class="chat-container">
    <div class="messages" id="messages"></div>
    <div class="input-area">
      <input class="input" id="input" placeholder="输入消息...">
      <button class="send-btn" onclick="sendMessage()">发送</button>
    </div>
  </div>
  <script>
    const publishId = window.location.pathname.split('/')[3];
    async function sendMessage() {
      const input = document.getElementById('input');
      const msg = input.value;
      if (!msg) return;

      const res = await fetch(`/public/agents/${publishId}/chat`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: msg})
      });
      const data = await res.json();

      const messages = document.getElementById('messages');
      messages.innerHTML += `<div><b>You:</b> ${msg}</div>`;
      messages.innerHTML += `<div><b>AI:</b> ${data.response}</div>`;
      input.value = '';
    }
  </script>
</body>
</html>'''


@router.get("/sdk/{publish_id}.js", response_class=Response)
async def get_sdk(publish_id: str):
    """JS SDK 文件"""
    js_code = (
        "(function(){"
        "window.MyRAGAgent={"
        "init:function(config){this.config=config||{};this.createWidget();},"
        "createWidget:function(){"
        "const btn=document.createElement('div');"
        "btn.id='myrag-agent-btn';"
        "btn.style.cssText='position:fixed;bottom:20px;right:20px;width:60px;height:60px;border-radius:50%;background:'+(this.config.theme||'#1890ff')+';cursor:pointer;display:flex;align-items:center;justify-content:center;color:white;font-size:24px;';"
        "btn.innerHTML='💬';"
        "btn.onclick=this.openWindow.bind(this);"
        "document.body.appendChild(btn);"
        "},"
        "openWindow:function(){"
        "if(this.window)return;"
        "this.window=document.createElement('iframe');"
        f"this.window.src='/public/embed/{publish_id}/';"
        "this.window.style.cssText='position:fixed;bottom:90px;right:20px;width:400px;height:500px;border:none;border-radius:8px;box-shadow:0 4px 20px rgba(0,0,0,0.2);';"
        "document.body.appendChild(this.window);"
        "this.btnClose=document.createElement('div');"
        "this.btnClose.style.cssText='position:fixed;bottom:595px;right:420px;width:30px;height:30px;border-radius:50%;background:#ff4d4f;color:white;display:flex;align-items:center;justify-content:center;cursor:pointer;';"
        "this.btnClose.innerHTML='✕';"
        "this.btnClose.onclick=this.closeWindow.bind(this);"
        "document.body.appendChild(this.btnClose);"
        "},"
        "closeWindow:function(){"
        "if(this.window){"
        "document.body.removeChild(this.window);"
        "document.body.removeChild(this.btnClose);"
        "this.window=null;"
        "this.btnClose=null;"
        "}"
        "}"
        "}"
        "})();"
    )
    return Response(content=js_code, media_type="application/javascript")