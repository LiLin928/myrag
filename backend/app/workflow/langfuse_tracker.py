"""Langfuse 链路追踪工具 (v3 SDK)

v3 SDK API 使用方式：
- 使用 start_as_current_observation() 上下文管理器创建 trace/span
- 支持 as_type: "span", "generation", "event"
- 使用 @observe() 装饰器追踪函数
"""

from typing import Dict, Any, Optional
import logging
from contextlib import contextmanager

from langfuse import Langfuse, observe
from langfuse.langchain import CallbackHandler

from app.config import get_settings

logger = logging.getLogger(__name__)

# Langfuse 客户端实例（单例）
_langfuse_client: Optional[Langfuse] = None


def get_langfuse_client() -> Optional[Langfuse]:
    """获取 Langfuse 客户端（单例模式）

    Returns:
        Langfuse 客户端，如果未启用返回 None
    """
    global _langfuse_client

    settings = get_settings()

    if not settings.langfuse_available:
        return None

    # 如果已经初始化，返回缓存的客户端
    if _langfuse_client is not None:
        return _langfuse_client

    try:
        _langfuse_client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
            timeout=60,
        )
        logger.info("Langfuse client initialized successfully")
        return _langfuse_client
    except Exception as e:
        logger.warning(f"Langfuse client initialization failed: {e}")
        return None


@contextmanager
def create_trace_context(
    name: str,
    input_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
):
    """创建 Trace 上下文管理器（推荐方式）

    使用 with 语句自动管理 trace 的创建和结束

    Args:
        name: Trace 名称
        input_data: 输入数据
        metadata: 元数据
        user_id: 用户 ID
        session_id: Session ID

    Yields:
        Observation 对象，如果未启用返回 None

    Example:
        with create_trace_context("my-workflow", input={"query": "test"}) as trace:
            # 执行工作流...
            trace.update(output={"result": "success"})
    """
    langfuse = get_langfuse_client()

    if not langfuse:
        yield None
        return

    try:
        with langfuse.start_as_current_observation(
            as_type="span",
            name=name,
            input=input_data or {},
            metadata={
                "user_id": user_id,
                "session_id": session_id,
                **(metadata or {}),
            },
        ) as trace:
            yield trace
    except Exception as e:
        logger.warning(f"Langfuse trace creation failed: {e}")
        yield None


@contextmanager
def create_span_context(
    name: str,
    input_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    parent: Optional[Any] = None,
):
    """创建 Span 上下文管理器

    Args:
        name: Span 名称
        input_data: 输入数据
        metadata: 元数据
        parent: 父级 Observation（可选）

    Yields:
        Observation 对象
    """
    langfuse = get_langfuse_client()

    if not langfuse:
        yield None
        return

    try:
        if parent:
            with parent.start_as_current_observation(
                as_type="span",
                name=name,
                input=input_data or {},
                metadata=metadata or {},
            ) as span:
                yield span
        else:
            with langfuse.start_as_current_observation(
                as_type="span",
                name=name,
                input=input_data or {},
                metadata=metadata or {},
            ) as span:
                yield span
    except Exception as e:
        logger.warning(f"Langfuse span creation failed: {e}")
        yield None


@contextmanager
def create_generation_context(
    name: str,
    model: Optional[str] = None,
    input_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    parent: Optional[Any] = None,
):
    """创建 Generation 上下文管理器（用于 LLM 调用）

    Args:
        name: Generation 名称
        model: 模型名称
        input_data: 输入数据
        metadata: 元数据
        parent: 父级 Observation

    Yields:
        Observation 对象
    """
    langfuse = get_langfuse_client()

    if not langfuse:
        yield None
        return

    try:
        if parent:
            with parent.start_as_current_observation(
                as_type="generation",
                name=name,
                input=input_data or {},
                metadata=metadata or {},
            ) as gen:
                yield gen
        else:
            with langfuse.start_as_current_observation(
                as_type="generation",
                name=name,
                input=input_data or {},
                metadata=metadata or {},
            ) as gen:
                yield gen
    except Exception as e:
        logger.warning(f"Langfuse generation creation failed: {e}")
        yield None


def get_langchain_handler() -> Optional[CallbackHandler]:
    """获取 LangChain CallbackHandler

    Returns:
        CallbackHandler，如果未启用返回 None
    """
    settings = get_settings()

    if not settings.langfuse_available:
        return None

    try:
        return CallbackHandler(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
    except Exception as e:
        logger.warning(f"Langfuse langchain handler creation failed: {e}")
        return None


def create_span_direct(
    trace_id: str,
    node_type: str,
    node_name: str,
    input_data: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    """直接创建 Span（非上下文管理器方式）

    用于节点追踪，需要手动调用 end_span()

    Args:
        trace_id: Trace ID（存储在 metadata 中用于关联）
        node_type: 节点类型
        node_name: 节点名称
        input_data: 输入数据
        metadata: 元数据

    Returns:
        Observation 对象，如果未启用返回 None
    """
    langfuse = get_langfuse_client()

    if not langfuse:
        return None

    try:
        span = langfuse.start_observation(
            name=f"{node_type}: {node_name}",
            input=input_data,
            metadata={
                "trace_id": trace_id,
                "node_type": node_type,
                **(metadata or {}),
            },
        )
        logger.debug(f"Langfuse span created: {node_type}/{node_name}")
        return span
    except Exception as e:
        logger.warning(f"Langfuse span creation failed: {e}")
        return None


def create_generation_direct(
    trace_id: str,
    model: str,
    input_data: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    """直接创建 Generation（用于 LLM 调用）

    Args:
        trace_id: Trace ID
        model: 模型名称
        input_data: 输入数据
        metadata: 元数据

    Returns:
        Observation 对象
    """
    langfuse = get_langfuse_client()

    if not langfuse:
        return None

    try:
        gen = langfuse.start_observation(
            name=f"LLM: {model}",
            input=input_data,
            metadata={
                "trace_id": trace_id,
                "model": model,
                **(metadata or {}),
            },
        )
        return gen
    except Exception as e:
        logger.warning(f"Langfuse generation creation failed: {e}")
        return None


def end_observation(
    observation: Optional[Any],
    output_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    usage: Optional[Dict[str, Any]] = None,
) -> None:
    """结束 Observation

    Args:
        observation: Observation 对象
        output_data: 输出数据
        metadata: 元数据
        usage: LLM usage 信息（如 tokens）
    """
    if observation is None:
        return

    try:
        update_data = {}
        if output_data:
            update_data["output"] = output_data
        if metadata:
            update_data["metadata"] = metadata
        if usage:
            update_data["usage"] = usage

        observation.update(**update_data)
        observation.end()
    except Exception as e:
        logger.warning(f"Langfuse observation end failed: {e}")


def flush_client() -> None:
    """刷新 Langfuse 客户端，确保数据写入（带超时保护）"""
    langfuse = get_langfuse_client()

    if langfuse:
        try:
            # 使用超时参数避免阻塞（langfuse v4 SDK 支持 timeout）
            langfuse.flush(timeout=5)
            logger.debug("Langfuse client flushed")
        except Exception as e:
            logger.warning(f"Langfuse flush failed: {e}")


def shutdown_client() -> None:
    """关闭 Langfuse 客户端"""
    global _langfuse_client

    if _langfuse_client:
        try:
            _langfuse_client.shutdown()
            _langfuse_client = None
        except Exception as e:
            logger.warning(f"Langfuse shutdown failed: {e}")


# 向后兼容函数
def create_trace(
    trace_id: str,
    name: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    """创建 Trace（向后兼容函数）

    Args:
        trace_id: Trace ID
        name: Trace 名称
        user_id: 用户 ID
        session_id: Session ID
        metadata: 元数据

    Returns:
        Observation 对象
    """
    langfuse = get_langfuse_client()

    if not langfuse:
        return None

    try:
        trace = langfuse.start_observation(
            name=name,
            input={"trace_id": trace_id},
            metadata={
                "trace_id": trace_id,
                "user_id": user_id,
                "session_id": session_id,
                **(metadata or {}),
            },
        )
        logger.info(f"Langfuse trace created: {trace_id}")
        return trace
    except Exception as e:
        logger.warning(f"Langfuse trace creation failed: {e}")
        return None


def end_trace(
    trace: Optional[Any],
    metadata: Optional[Dict[str, Any]] = None,
    output: Optional[Dict[str, Any]] = None,
) -> None:
    """结束 Trace（向后兼容函数）"""
    end_observation(trace, output_data=output, metadata=metadata)


def update_trace(
    trace: Optional[Any],
    metadata: Optional[Dict[str, Any]] = None,
    output: Optional[Dict[str, Any]] = None,
) -> None:
    """更新 Trace（向后兼容函数）"""
    if trace is None:
        return
    try:
        trace.update(metadata=metadata or {}, output=output or {})
    except Exception as e:
        logger.warning(f"Langfuse trace update failed: {e}")


def end_span(
    span: Optional[Any],
    output_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """结束 Span（向后兼容函数）"""
    end_observation(span, output_data=output_data, metadata=metadata)


# 导出装饰器供直接使用
def traced_function(name: Optional[str] = None):
    """函数追踪装饰器

    Example:
        @traced_function("my-function")
        def process_query(query: str) -> dict:
            return {"result": query}
    """
    return observe(name=name)