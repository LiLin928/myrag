"""文档处理状态机

LangGraph 处理轻量级流程：
- 结构化抽取
- 条款索引
- 知识预编译
- 触发 ARQ 向量化

ARQ 已完成重解析（MinerU/Unstructured），LangGraph 处理后续流程
"""

from typing import TypedDict, Annotated, Dict, Any, List, Literal, Optional
from langgraph.graph import StateGraph, END
from datetime import datetime


class DocumentFlowState(TypedDict):
    """文档处理状态（LangGraph 管理）"""

    document_id: str
    user_id: str
    parsed_content: List[Dict[str, Any]]  # ARQ 已完成解析
    structured_data: Dict[str, Any]
    clauses: List[Dict[str, Any]]
    knowledge: Dict[str, Any]
    current_stage: Literal["extract", "index", "compile", "vectorize_trigger", "completed"]
    error: Optional[str]


async def extract_structure(state: DocumentFlowState) -> Dict[str, Any]:
    """第二层：结构化抽取（轻量级）

    提取标题、段落、列表结构
    """
    # TODO: 实现真实结构化抽取逻辑

    structured_data = {
        "titles": [],
        "paragraphs": [],
        "tables": [],
    }

    for block in state["parsed_content"]:
        block_type = block.get("type")
        if block_type == "text":
            # 简单分析：检测标题
            content = block.get("content", "")
            if content.startswith("#"):
                structured_data["titles"].append(content)
            else:
                structured_data["paragraphs"].append(content)
        elif block_type == "table":
            structured_data["tables"].append(block)

    return {
        "current_stage": "index",
        "structured_data": structured_data,
    }


async def index_clauses(state: DocumentFlowState) -> Dict[str, Any]:
    """第三层：条款索引

    使用 ClauseSplitter 分块
    """
    from app.rag.splitter.clause_splitter import ClauseSplitter

    splitter = ClauseSplitter()
    clause_blocks = splitter.split(state["parsed_content"])

    clauses = splitter.to_dict_list(clause_blocks)

    return {
        "current_stage": "compile",
        "clauses": clauses,
    }


async def compile_knowledge(state: DocumentFlowState) -> Dict[str, Any]:
    """第四层：知识预编译

    生成摘要、问答对（LLM 调用）
    """
    # TODO: 实现真实知识预编译
    # 使用 LLM 生成摘要和问答对

    knowledge = {
        "summary": "文档摘要占位",
        "qa_pairs": [],
        "key_entities": [],
    }

    return {
        "current_stage": "vectorize_trigger",
        "knowledge": knowledge,
    }


async def trigger_vectorization(state: DocumentFlowState) -> Dict[str, Any]:
    """触发 ARQ 向量化任务

    将向量化任务提交给 ARQ
    """
    from app.tasks import get_redis_pool

    # 获取 Redis 连接池
    pool = await get_redis_pool()

    # 提交向量化任务
    job = await pool.enqueue_job(
        "vectorize_chunks",
        state["document_id"],
        state["clauses"],
        state["user_id"],
    )

    return {
        "current_stage": "completed",
        "knowledge": {
            **state["knowledge"],
            "vectorize_job_id": job.job_id,
        }
    }


def create_document_flow_graph() -> StateGraph:
    """创建文档处理状态图

    Returns:
        StateGraph: 文档处理状态图
    """
    graph = StateGraph(DocumentFlowState)

    # 添加节点
    graph.add_node("extract", extract_structure)
    graph.add_node("index", index_clauses)
    graph.add_node("compile", compile_knowledge)
    graph.add_node("vectorize_trigger", trigger_vectorization)

    # 设置入口
    graph.set_entry_point("extract")

    # 添加边
    graph.add_edge("extract", "index")
    graph.add_edge("index", "compile")
    graph.add_edge("compile", "vectorize_trigger")
    graph.add_edge("vectorize_trigger", END)

    return graph


async def run_document_flow(
    document_id: str,
    user_id: str,
    parsed_content: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """运行文档处理流程

    Args:
        document_id: 文档 ID
        user_id: 用户 ID
        parsed_content: ARQ 解析结果

    Returns:
        处理结果
    """
    from app.graphs.checkpointer import get_checkpointer

    graph = create_document_flow_graph()
    checkpointer = get_checkpointer()
    compiled = graph.compile(checkpointer=checkpointer)

    thread_id = f"doc_flow_{document_id}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = DocumentFlowState(
        document_id=document_id,
        user_id=user_id,
        parsed_content=parsed_content,
        structured_data={},
        clauses=[],
        knowledge={},
        current_stage="extract",
        error=None,
    )

    result = await compiled.invoke(initial_state, config)
    return result