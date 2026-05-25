# app/agent/middleware/__init__.py

"""Agent 中间件模块

三层中间件架构：
1. dynamic_deepseek_routing: @wrap_model_call 动态模型路由
2. trim_messages: @before_model 消息压缩
3. human_approval_middleware: HumanInTheLoopMiddleware 人工审批
"""

from app.agent.middleware.dynamic_router import (
    dynamic_deepseek_routing,
    COMPLEX_KEYWORDS,
)
from app.agent.middleware.message_compression import (
    trim_messages,
    MAX_MESSAGES,
)
from app.agent.middleware.human_approval import (
    human_approval_middleware,
    SENSITIVE_TOOLS,
)

__all__ = [
    # Dynamic Router
    "dynamic_deepseek_routing",
    "COMPLEX_KEYWORDS",
    # Message Compression
    "trim_messages",
    "MAX_MESSAGES",
    # Human Approval
    "human_approval_middleware",
    "SENSITIVE_TOOLS",
]