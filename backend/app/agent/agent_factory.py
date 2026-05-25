# app/agent/agent_factory.py

"""Agent Factory - create_agent 统一入口

使用 LangChain 1.x create_agent API，集成三层中间件：
- dynamic_deepseek_routing: 动态模型路由
- trim_messages: 消息压缩
- human_approval_middleware: 人工审批
"""

from typing import List, Optional
from langchain.agents import create_agent
from langchain_core.tools import BaseTool
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
import logging

from app.config import get_settings
from app.tools.tool_registry import get_all_tools
from app.agent.middleware import (
    dynamic_deepseek_routing,
    trim_messages,
    human_approval_middleware,
)

settings = get_settings()
logger = logging.getLogger(__name__)

# 默认系统提示
DEFAULT_SYSTEM_PROMPT = """你是 MyRAG 智能助手，具备以下能力：

1. 知识库检索：从用户指定的知识库中检索相关信息
2. HTTP 请求：调用外部 API 获取数据
3. 代码执行：在沙盒环境中安全执行 Python 代码

请根据用户请求选择合适的工具完成任务。

注意事项：
- 对于敏感操作（代码执行、外部请求），系统会要求人工确认
- 复杂问题会自动启用深度推理模式
"""


def get_default_checkpointer() -> BaseCheckpointSaver:
    """获取默认 Checkpointer

    优先使用 PostgresSaver，失败则 fallback 到 InMemorySaver

    Returns:
        Checkpointer 实例
    """
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        from app.graphs.checkpointer import get_checkpointer
        return get_checkpointer()
    except Exception as e:
        logger.warning(f"PostgresSaver 初始化失败，使用 InMemorySaver: {e}")
        return InMemorySaver()


def create_myrag_agent(
    checkpointer: Optional[BaseCheckpointSaver] = None,
    system_prompt: Optional[str] = None,
    tools: Optional[List[BaseTool]] = None,
    enable_dynamic_router: bool = True,
    enable_message_compression: bool = True,
    enable_human_approval: bool = True,
) -> "CompiledGraph":
    """创建 MyRAG Agent（使用 create_agent + middleware）

    Args:
        checkpointer: Checkpointer 实例，None 则使用默认
        system_prompt: 系统提示词
        tools: 工具列表，None 则使用 get_all_tools()
        enable_dynamic_router: 是否启用动态模型路由
        enable_message_compression: 是否启用消息压缩
        enable_human_approval: 是否启用人工审批

    Returns:
        CompiledGraph: 编译后的 Agent
    """
    # 1. 初始化模型
    model = ChatDeepSeek(
        model=settings.DEEPSEEK_CHAT_MODEL,
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_API_BASE,
        temperature=0.7,
    )

    # 2. 获取工具
    agent_tools = tools or get_all_tools()

    # 3. 构建 middleware 列表
    middleware = []
    if enable_dynamic_router:
        middleware.append(dynamic_deepseek_routing)
    if enable_message_compression:
        middleware.append(trim_messages)
    if enable_human_approval:
        middleware.append(human_approval_middleware)

    # 4. Checkpointer
    if checkpointer is None:
        checkpointer = get_default_checkpointer()

    # 5. 创建 Agent
    agent = create_agent(
        model=model,
        tools=agent_tools,
        middleware=middleware,
        checkpointer=checkpointer,
        system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPT,
    )

    return agent