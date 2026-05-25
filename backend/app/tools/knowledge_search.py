"""知识检索工具

从项目知识库检索相关文档片段，支持：
- 向量检索（语义相似）
- 混合检索（向量 + 关键词）
- 元数据过滤（供应商、条款类型等）
"""

from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from app.rag.retrieval.pgvector_retriever import PGVectorRetriever
from app.rag.retrieval.hybrid_retriever import HybridRetriever


@tool
async def knowledge_search(
    query: str,
    knowledge_base_id: str = None,
    project_id: str = None,  # 向后兼容，已弃用
    top_k: int = 5,
    score_threshold: float = 0.0,
    # 元数据过滤参数
    supplier: Optional[str] = None,
    clause_type: Optional[str] = None,
    document_type: Optional[str] = None,
    section: Optional[str] = None,
    # 检索模式
    use_hybrid: bool = True,
) -> List[Dict[str, Any]]:
    """从知识库中检索相关文档片段

    支持元数据过滤，适用于投标文件等结构化文档场景。

    Args:
        query: 搜索查询文本
        knowledge_base_id: 知识库 ID（推荐使用）
        project_id: 项目 ID（向后兼容，已弃用，请使用 knowledge_base_id）
        top_k: 返回结果数量，默认 5
        score_threshold: 相似度阈值，默认 0.0
        supplier: 供应商名称过滤，如 "供应商A"
        clause_type: 条款类型过滤，如 "price_table", "technical_clause"
        document_type: 文档类型过滤，如 "投标文件", "招标文件"
        section: 章节过滤，如 "商务部分", "技术部分"
        use_hybrid: 是否使用混合检索（向量+关键词），默认 True

    Returns:
        相关文档片段列表，每个片段包含：
        - content: 文本内容
        - source: 来源文档 ID
        - score: 相关性分数
        - metadata: 元数据（clause_id, clause_type, page_number, supplier）

    Example:
        # 搜索知识库中的报价信息
        knowledge_search(
            query="报价明细",
            knowledge_base_id="kb_001",
            clause_type="price_table"
        )
    """
    # 统一参数：优先使用 knowledge_base_id
    kb_id = knowledge_base_id or project_id
    if not kb_id:
        return [{"error": "knowledge_base_id is required"}]
    # 构建过滤条件
    filters = {}
    if supplier:
        filters["supplier"] = supplier
    if clause_type:
        filters["clause_type"] = clause_type
    if document_type:
        filters["document_type"] = document_type
    if section:
        filters["section"] = section

    # 选择检索器
    if use_hybrid:
        retriever = HybridRetriever(
            project_id=int(kb_id),
            top_k=top_k,
            score_threshold=score_threshold,
        )
    else:
        retriever = PGVectorRetriever(
            project_id=int(kb_id),
            top_k=top_k,
            score_threshold=score_threshold,
        )

    # 执行检索
    results = await retriever.search(query, filters=filters if filters else None)

    # 格式化输出
    formatted_results = []
    for result in results:
        metadata = result.get("metadata", {})
        formatted_results.append({
            "content": result["content"],
            "source": f"document_{result.get('document_id', 'unknown')}",
            "score": result["score"],
            "metadata": {
                "clause_id": result.get("clause_id"),
                "clause_type": result.get("clause_type"),
                "clause_title": result.get("clause_title"),
                "page_number": result.get("page_number"),
                "chunk_id": result.get("id"),
                "supplier": metadata.get("supplier"),
                "document_type": metadata.get("document_type"),
                "section": metadata.get("section"),
            },
            "search_type": result.get("search_type", "vector"),
        })

    return formatted_results


@tool
async def search_by_supplier(
    query: str,
    supplier: str,  # 必填参数
    knowledge_base_id: str = None,
    project_id: str = None,  # 向后兼容，已弃用
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """按供应商检索文档内容

    专门用于投标文件场景，快速定位特定供应商的相关信息。

    Args:
        query: 搜索查询文本
        supplier: 供应商名称（必填）
        knowledge_base_id: 知识库 ID（推荐使用）
        project_id: 项目 ID（向后兼容，已弃用）
        top_k: 返回结果数量

    Returns:
        该供应商的相关文档片段

    Example:
        search_by_supplier(
            query="报价金额",
            supplier="供应商B",
            knowledge_base_id="kb_001"
        )
    """
    kb_id = knowledge_base_id or project_id
    retriever = HybridRetriever(project_id=int(kb_id), top_k=top_k)

    results = await retriever.search(
        query,
        filters={"supplier": supplier}
    )

    return [
        {
            "content": r["content"],
            "source": f"document_{r.get('document_id', 'unknown')}",
            "score": r["score"],
            "metadata": r.get("metadata", {}),
        }
        for r in results
    ]


@tool
async def search_by_clause_type(
    query: str,
    clause_type: str,  # 必填参数
    knowledge_base_id: str = None,
    project_id: str = None,  # 向后兼容，已弃用
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """按条款类型检索文档内容

    用于定位特定类型的条款，如报价单、技术条款、商务条款等。

    Args:
        query: 搜索查询文本
        clause_type: 条款类型（必填）
            - price_table: 报价表/价格条款
            - technical_clause: 技术条款/参数要求
            - commercial_clause: 商务条款
            - legal_clause: 法律条款
            - qualification: 资质要求
        knowledge_base_id: 知识库 ID（推荐使用）
        project_id: 项目 ID（向后兼容，已弃用）
        top_k: 返回结果数量

    Returns:
        该类型的条款内容

    Example:
        # 搜索所有技术参数要求
        search_by_clause_type(
            query="服务器配置",
            clause_type="technical_clause",
            knowledge_base_id="kb_001"
        )
    """
    kb_id = knowledge_base_id or project_id
    retriever = HybridRetriever(project_id=int(kb_id), top_k=top_k)

    results = await retriever.search(
        query,
        filters={"clause_type": clause_type}
    )

    return [
        {
            "content": r["content"],
            "source": f"document_{r.get('document_id', 'unknown')}",
            "score": r["score"],
            "clause_title": r.get("clause_title"),
            "page_number": r.get("page_number"),
        }
        for r in results
    ]


@tool
async def search_all_projects(
    query: str,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """跨所有项目检索

    Args:
        query: 搜索查询文本
        top_k: 返回结果数量

    Returns:
        检索结果列表
    """
    retriever = HybridRetriever(top_k=top_k)
    results = await retriever.search(query)

    return [
        {
            "content": r["content"],
            "source": f"document_{r.get('document_id', 'unknown')}",
            "score": r["score"],
            "metadata": r.get("metadata", {}),
        }
        for r in results
    ]


def create_knowledge_search_tools() -> List:
    """创建所有知识检索工具"""
    return [
        knowledge_search,
        search_by_supplier,
        search_by_clause_type,
        search_all_projects,
    ]


def create_knowledge_search_tool() -> knowledge_search:
    """创建知识检索工具实例"""
    return knowledge_search