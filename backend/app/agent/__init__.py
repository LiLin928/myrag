# app/agent/__init__.py

"""Agent 模块

LangChain 1.x Agent 架构实现，包含：
- agent_factory: create_agent 封装
- middleware: 中间件系统（动态路由、消息压缩、人工审批）
"""

from app.agent.agent_factory import (
    create_myrag_agent,
    get_default_checkpointer,
    DEFAULT_SYSTEM_PROMPT,
)

__all__ = [
    "create_myrag_agent",
    "get_default_checkpointer",
    "DEFAULT_SYSTEM_PROMPT",
]