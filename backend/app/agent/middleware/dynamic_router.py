"""动态模型路由中间件

使用 @wrap_model_call 装饰器，根据问题复杂度动态选择模型：
- 简单问题 → deepseek-chat（快速、低成本）
- 复杂问题 → deepseek-reasoner（深度推理）
"""

from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage
from app.config import get_settings

settings = get_settings()

# 延迟初始化模型（避免模块加载时就需要 API_KEY）
_chat_model = None
_reasoner_model = None


def _get_models():
    """延迟初始化模型"""
    global _chat_model, _reasoner_model

    if _chat_model is None:
        _chat_model = ChatDeepSeek(
            model=settings.DEEPSEEK_CHAT_MODEL,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_API_BASE,
        )
        _reasoner_model = ChatDeepSeek(
            model=settings.DEEPSEEK_REASONER_MODEL,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_API_BASE,
        )

    return _chat_model, _reasoner_model


# 复杂问题关键词
COMPLEX_KEYWORDS = (
    "证明", "推导", "规划", "step-by-step",
    "chain of thought", "数学", "逻辑",
    "分析", "比较", "评估", "决策",
)


def _get_last_user_text(messages) -> str:
    """获取最后一个用户消息的文本内容

    Args:
        messages: 消息列表

    Returns:
        最后一个用户消息的文本，若无则返回空字符串
    """
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            content = m.content
            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                # 处理多模态消息
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        return part.get("text", "")
    return ""


def _is_complex_query(messages, last_user_text: str) -> bool:
    """判断是否为复杂查询

    判断规则：
    1. 消息数 > 10 → 复杂
    2. 最后用户消息 > 120 字 → 复杂
    3. 包含复杂关键词 → 复杂

    Args:
        messages: 消息列表
        last_user_text: 最后用户消息文本

    Returns:
        是否为复杂查询
    """
    # 规则 1: 消息数过多
    if len(messages) > 10:
        return True

    # 规则 2: 文本过长
    if len(last_user_text) > 120:
        return True

    # 规则 3: 包含复杂关键词
    text_lower = last_user_text.lower()
    for kw in COMPLEX_KEYWORDS:
        if kw.lower() in text_lower:
            return True

    return False


@wrap_model_call
def dynamic_deepseek_routing(request: ModelRequest, handler) -> ModelResponse:
    """动态模型路由中间件

    作为 @wrap_model_call 类型中间件，在模型调用前
    根据问题复杂度动态选择模型。

    Args:
        request: 模型请求对象，包含 state 和 model
        handler: 下游处理器

    Returns:
        模型响应
    """
    chat_model, reasoner_model = _get_models()

    messages = request.state.get("messages", [])
    last_user_text = _get_last_user_text(messages)

    is_complex = _is_complex_query(messages, last_user_text)

    request.model = reasoner_model if is_complex else chat_model

    return handler(request)