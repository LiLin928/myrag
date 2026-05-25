"""知识库检索 API

支持：
- 向量检索
- 关键词检索
- 混合检索
- Rerank 重排序
- 元数据过滤
"""

from fastapi import APIRouter, Depends, Query, Path, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field
import time
import uuid
import logging

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.db import get_db
from app.rag.retrieval.hybrid_retriever import HybridRetriever
from app.rag.retrieval.pgvector_retriever import PGVectorRetriever
from app.services.retrieval_service import get_retrieval_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge-search"])


class SearchTestRequest(BaseModel):
    """检索测试请求"""
    query: str = Field(..., description="查询文本")
    top_k: int = Field(5, ge=1, le=50, description="返回数量")
    score_threshold: float = Field(0.5, ge=0.0, le=1.0, description="相似度阈值")
    search_type: str = Field("hybrid", description="检索类型: vector/hybrid/keyword")
    filters: Optional[Dict[str, Any]] = Field(None, description="元数据过滤条件")


class SearchTestResult(BaseModel):
    """检索测试结果"""
    chunk_id: str
    document_id: str
    content: str
    score: float
    clause_type: Optional[str] = None
    section_title: Optional[str] = None
    page_number: int = 1
    metadata: Dict[str, Any] = Field(default_factory=dict)
    search_method: str = "vector"


class SearchTestResponse(BaseModel):
    """检索测试响应"""
    query: str
    search_type: str
    filters: Optional[Dict[str, Any]] = None
    results: List[SearchTestResult]
    performance: Dict[str, Any] = Field(default_factory=dict)


# ==================== 知识库检索 API ====================


class SearchRequest(BaseModel):
    """知识库检索请求"""
    query: str = Field(..., min_length=1, max_length=500, description="查询文本")
    top_k: Optional[int] = Field(None, ge=1, le=100, description="返回数量（使用知识库配置）")
    search_type: Optional[Literal["vector", "hybrid", "keyword"]] = Field(None, description="检索类型（可选，覆盖知识库配置）")
    filters: Optional[Dict[str, Any]] = Field(None, description="元数据过滤条件")


class SearchResultItem(BaseModel):
    """检索结果项"""
    id: str = Field(..., description="分块 ID")
    content: str = Field(..., description="文本内容")
    document_id: str = Field(..., description="文档 ID")
    filename: Optional[str] = Field(None, description="文档文件名")
    page_number: Optional[int] = Field(None, description="页码")
    section_title: Optional[str] = Field(None, description="章节标题")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    score: float = Field(..., description="最终相似度分数")
    vector_score: Optional[float] = Field(None, description="向量检索分数")
    keyword_score: Optional[float] = Field(None, description="关键词检索分数")
    rerank_score: Optional[float] = Field(None, description="Rerank 分数")


class SearchResponse(BaseModel):
    """知识库检索响应"""
    knowledge_id: str = Field(..., description="知识库 ID")
    query: str = Field(..., description="查询文本")
    method: str = Field(..., description="检索方法: vector/keyword/hybrid")
    total: int = Field(..., description="结果总数")
    results: List[SearchResultItem] = Field(..., description="检索结果列表")


@router.post("/{knowledge_id}/search", response_model=SearchResponse)
async def search_knowledge_base(
    knowledge_id: str = Path(..., description="知识库 ID"),
    request: SearchRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchResponse:
    """知识库检索

    根据知识库配置自动选择检索方式：
    - vector: 纯向量相似度检索
    - keyword: PostgreSQL 全文搜索
    - hybrid: 向量 + 关键词混合检索（加权融合）

    如果知识库启用了 Rerank，会在混合检索后进行重排序。

    Example:
        POST /api/knowledge/abc123/search
        {
            "query": "产品质量标准",
            "top_k": 10,
            "filters": {
                "document_id": "doc-uuid"
            }
        }
    """
    # 1. UUID 验证
    try:
        uuid.UUID(knowledge_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的知识库 ID 格式")

    # 2. 检查知识库是否存在及用户权限
    query = select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id)
    result = await db.execute(query)
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    if kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限操作此知识库")

    # 3. 执行检索
    try:
        retrieval_service = get_retrieval_service()
        search_result = await retrieval_service.search(
            knowledge_base_id=knowledge_id,
            query=request.query,
            db=db,
            top_k=request.top_k,
            filters=request.filters,
            search_type=request.search_type,
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except ValueError as e:
        logger.error(f"Search validation error for kb={knowledge_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Search failed for kb={knowledge_id}: {e}")
        raise HTTPException(status_code=500, detail="检索服务暂时不可用")

    # 4. 构建响应
    results = []
    for item in search_result.get("results", []):
        metadata = item.get("metadata", {})
        results.append(SearchResultItem(
            id=str(item.get("id", "")),
            content=item.get("content", ""),
            document_id=str(item.get("document_id", "")),
            filename=item.get("document_filename"),
            page_number=item.get("page_number"),
            section_title=metadata.get("section_title"),
            metadata=metadata,
            score=item.get("score", 0.0),
            vector_score=item.get("vector_score"),
            keyword_score=item.get("keyword_score"),
            rerank_score=item.get("rerank_score"),
        ))

    return SearchResponse(
        knowledge_id=knowledge_id,
        query=request.query,
        method=search_result.get("method", "unknown"),
        total=search_result.get("total", 0),
        results=results,
    )


# ==================== 检索测试 API（旧版，保留兼容） ====================


@router.post("/projects/{project_id}/test-search")
async def test_search(
    project_id: str = Path(..., description="项目 ID"),
    request: SearchTestRequest = Body(...),
    current_user: User = Depends(get_current_user),
) -> SearchTestResponse:
    """检索测试

    支持三种检索类型：
    - vector: 纯向量检索
    - hybrid: 混合检索（向量 + 关键词）
    - keyword: 纯关键词检索

    元数据过滤支持：
    - document_type: 文档类型 (PDF/Word/Markdown)
    - section_title: 章节标题
    - user_tags: 用户标签（数组）
    - category: 分类
    - position_type: 位置类型 (header/body/table)

    Example:
        POST /api/knowledge/projects/abc123/test-search
        {
            "query": "产品质量标准",
            "top_k": 5,
            "search_type": "hybrid",
            "filters": {
                "document_type": "PDF",
                "user_tags": ["重要"]
            }
        }
    """
    start_time = time.time()

    # 选择检索器
    if request.search_type == "hybrid":
        retriever = HybridRetriever(
            project_id=int(project_id) if project_id.isdigit() else None,
            top_k=request.top_k * 2,
            score_threshold=0.0,
        )
    elif request.search_type == "vector":
        retriever = PGVectorRetriever(
            project_id=int(project_id) if project_id.isdigit() else None,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
        )
    else:  # keyword
        retriever = HybridRetriever(
            project_id=int(project_id) if project_id.isdigit() else None,
            top_k=request.top_k,
            vector_weight=0.0,
            keyword_weight=1.0,
        )

    # 执行检索
    query_start = time.time()
    results = await retriever.search(request.query, filters=request.filters)
    query_time = (time.time() - query_start) * 1000  # ms

    # 过滤低于阈值的结果
    if request.score_threshold > 0:
        results = [r for r in results if r.get("score", 0) >= request.score_threshold]

    # 限制数量
    results = results[:request.top_k]

    total_time = (time.time() - start_time) * 1000  # ms

    # 构建响应
    search_results = [
        SearchTestResult(
            chunk_id=str(r.get("id")),
            document_id=str(r.get("document_id")),
            content=r.get("content"),
            score=r.get("score", 0),
            clause_type=r.get("clause_type"),
            section_title=r.get("metadata", {}).get("section_title") or r.get("section_title"),
            page_number=r.get("page_number", 1),
            metadata=r.get("metadata", {}),
            search_method=r.get("source", request.search_type),
        )
        for r in results
    ]

    return SearchTestResponse(
        query=request.query,
        search_type=request.search_type,
        filters=request.filters,
        results=search_results,
        performance={
            "query_time_ms": round(query_time, 2),
            "total_time_ms": round(total_time, 2),
            "result_count": len(results),
            "top_scores": [r.get("score", 0) for r in results[:5]],
        },
    )


@router.get("/projects/{project_id}/search-stats")
async def get_search_stats(
    project_id: str = Path(..., description="项目 ID"),
    db: Any = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取检索统计信息

    Returns:
        - total_chunks: 总分块数
        - vectorized_chunks: 已向量化数
        - avg_query_time: 平均查询耗时（如有历史）
    """
    from sqlalchemy import select, func
    from app.models.document import Document, DocumentChunk

    # 统计总分块数
    chunk_count_query = select(func.count()).select_from(DocumentChunk).where(
        DocumentChunk.project_id == project_id
    )
    chunk_result = await db.execute(chunk_count_query)
    total_chunks = chunk_result.scalar() or 0

    # 统计已向量化数
    vectorized_query = select(func.count()).select_from(DocumentChunk).where(
        DocumentChunk.project_id == project_id,
        DocumentChunk.embedding_vector.isnot(None),
    )
    vectorized_result = await db.execute(vectorized_query)
    vectorized_chunks = vectorized_result.scalar() or 0

    # 统计文档数
    doc_count_query = select(func.count()).select_from(Document).where(
        Document.project_id == project_id
    )
    doc_result = await db.execute(doc_count_query)
    document_count = doc_result.scalar() or 0

    return {
        "project_id": project_id,
        "document_count": document_count,
        "total_chunks": total_chunks,
        "vectorized_chunks": vectorized_chunks,
        "vectorization_rate": round(vectorized_chunks / total_chunks * 100, 2) if total_chunks > 0 else 0,
    }


@router.get("/projects/{project_id}/filter-options")
async def get_filter_options(
    project_id: str = Path(..., description="项目 ID"),
    db: Any = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取过滤选项（用于前端下拉菜单）

    Returns:
        - document_types: 文档类型列表
        - sections: 章节标题列表
        - user_tags: 所有用户标签列表
        - categories: 分类列表
    """
    from sqlalchemy import select, text

    # 文档类型
    doc_types_query = text("""
        SELECT DISTINCT document_type
        FROM document_chunks
        WHERE project_id = :project_id AND document_type IS NOT NULL
    """)
    doc_types_result = await db.execute(doc_types_query, {"project_id": project_id})
    document_types = [row[0] for row in doc_types_result.fetchall()]

    # 章节标题
    sections_query = text("""
        SELECT DISTINCT section_title
        FROM document_chunks
        WHERE project_id = :project_id AND section_title IS NOT NULL
        ORDER BY section_title
    """)
    sections_result = await db.execute(sections_query, {"project_id": project_id})
    sections = [row[0] for row in sections_result.fetchall()]

    # 用户标签（从 user_metadata JSON 中提取）
    tags_query = text("""
        SELECT DISTINCT jsonb_array_elements_text(user_metadata->'user_tags') as tag
        FROM document_chunks
        WHERE project_id = :project_id
          AND user_metadata->'user_tags' IS NOT NULL
    """)
    tags_result = await db.execute(tags_query, {"project_id": project_id})
    user_tags = [row[0] for row in tags_result.fetchall()]

    # 分类
    categories_query = text("""
        SELECT DISTINCT user_metadata->>'category' as category
        FROM document_chunks
        WHERE project_id = :project_id
          AND user_metadata->>'category' IS NOT NULL
    """)
    categories_result = await db.execute(categories_query, {"project_id": project_id})
    categories = [row[0] for row in categories_result.fetchall()]

    return {
        "document_types": document_types,
        "sections": sections,
        "user_tags": user_tags,
        "categories": categories,
    }