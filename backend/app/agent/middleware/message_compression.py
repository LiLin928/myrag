"""消息压缩中间件

使用 @before_model 装饰器，在模型调用前修剪历史消息：
- 保留第一条消息（系统提示/初始用户消息）
- 保留最近 MAX_MESSAGES-1 条消息
- 中间消息被修剪
"""

from langchain.agents.middleware import before_model
from langchain.agents import AgentState
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.runtime import Runtime
from typing import Any

MAX_MESSAGES = 20


@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """修剪消息历史

    作为 @before_model 类型中间件，在模型调用前
    修剪过长的消息历史。

    Args:
        state: Agent 状态，包含 "messages" 字段
        runtime: LangGraph Runtime

    Returns:
        若需要修剪，返回新的 messages 列表；
        否则返回 None（不修改）
    """
    messages = state["messages"]

    # 不超过阈值，不压缩
    if len(messages) <= MAX_MESSAGES:
        return None

    # 保留第一条 + 最近的消息
    first_msg = messages[0]
    recent_msgs = messages[-(MAX_MESSAGES - 1):]

    new_messages = [first_msg] + recent_msgs

    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages
        ]
    }