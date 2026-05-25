"""Langfuse 链路追踪工具"""

from typing import Dict, Any, Optional
import logging

from langfuse import Langfuse

from app.config import get_settings

logger = logging.getLogger(__name__)


def get_langfuse_client() -> Optional[Langfuse]:
    """获取 Langfuse 客户端

    Returns:
        Langfuse 客户端，如果未启用返回 None
    """
    settings = get_settings()

    if not settings.langfuse_available:
        return None

    try:
        return Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
    except Exception as e:
        logger.warning(f"Langfuse client initialization failed: {e}")
        return None


def create_trace(
    trace_id: str,
    name: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    """创建 Trace

    Args:
        trace_id: Trace ID
        name: Trace 名称
        user_id: 用户 ID
        session_id: Session ID
        metadata: 元数据

    Returns:
        Trace 对象，如果未启用返回 None
    """
    langfuse = get_langfuse_client()

    if not langfuse:
        return None

    try:
        return langfuse.trace(
            id=trace_id,
            name=name,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {},
        )
    except Exception as e:
        logger.warning(f"Langfuse trace creation failed: {e}")
        return None


def get_langchain_handler(trace: Optional[Any]) -> Optional[Any]:
    """获取 LangChain CallbackHandler

    Args:
        trace: Trace 对象

    Returns:
        LangchainCallbackHandler，如果 trace 为 None 返回 None
    """
    if trace is None:
        return None

    try:
        return trace.get_langchain_handler()
    except Exception as e:
        logger.warning(f"Langfuse langchain handler creation failed: {e}")
        return None


def create_span(
    trace_id: str,
    node_type: str,
    node_name: str,
    input_data: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    """创建 Span

    Args:
        trace_id: Trace ID
        node_type: 节点类型
        node_name: 节点名称
        input_data: 输入数据
        metadata: 元数据

    Returns:
        Span 对象，如果未启用返回 None
    """
    langfuse = get_langfuse_client()

    if not langfuse:
        return None

    try:
        trace = langfuse.get_trace(trace_id)
        return trace.span(
            name=f"{node_type}: {node_name}",
            input=input_data,
            metadata=metadata or {},
        )
    except Exception as e:
        logger.warning(f"Langfuse span creation failed: {e}")
        return None


def end_span(
    span: Optional[Any],
    output_data: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """结束 Span

    Args:
        span: Span 对象
        output_data: 输出数据
        metadata: 元数据
    """
    if span is None:
        return

    try:
        span.end(
            output=output_data,
            metadata=metadata or {},
        )
    except Exception as e:
        logger.warning(f"Langfuse span end failed: {e}")


def update_trace(
    trace: Optional[Any],
    metadata: Optional[Dict[str, Any]] = None,
    output: Optional[Dict[str, Any]] = None,
) -> None:
    """更新 Trace

    Args:
        trace: Trace 对象
        metadata: 元数据
        output: 输出数据
    """
    if trace is None:
        return

    try:
        trace.update(
            metadata=metadata or {},
            output=output,
        )
    except Exception as e:
        logger.warning(f"Langfuse trace update failed: {e}")


def flush_client() -> None:
    """刷新 Langfuse 客户端，确保数据写入"""
    langfuse = get_langfuse_client()

    if langfuse:
        try:
            langfuse.flush()
        except Exception as e:
            logger.warning(f"Langfuse flush failed: {e}")