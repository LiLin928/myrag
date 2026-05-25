"""API 路由"""
from fastapi import APIRouter

from app.api.routes import auth, users, websocket, documents, skills, knowledge, search, workflows, agents, conversations, models, agent, multi_agent, knowledge_chunks, knowledge_documents, knowledge_search, workflow_websocket, workflow_templates, agent_sessions, agent_publish, agent_public, tools, mcp, system_prompts, metadata

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(websocket.router)
api_router.include_router(documents.router)
api_router.include_router(skills.router)
api_router.include_router(knowledge.router)
api_router.include_router(search.router)
api_router.include_router(workflows.router)
api_router.include_router(agents.router)
api_router.include_router(agent.router)
api_router.include_router(agent_sessions.router)
api_router.include_router(agent_publish.router)
api_router.include_router(agent_public.router)
api_router.include_router(conversations.router)
api_router.include_router(models.router)
api_router.include_router(multi_agent.router)
api_router.include_router(knowledge_chunks.router)
api_router.include_router(knowledge_documents.router)
api_router.include_router(knowledge_search.router)
api_router.include_router(workflow_websocket.router)
api_router.include_router(workflow_templates.router)
api_router.include_router(tools.router)
api_router.include_router(mcp.router)
api_router.include_router(system_prompts.router)
api_router.include_router(metadata.router)
