"""搜索 API 路由

支持：
- 项目内搜索（支持元数据过滤）
- 按供应商搜索
- 按条款类型搜索
- 全局搜索
"""

from fastapi import APIRouter, Depends, Body
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.rag.retrieval.hybrid_retriever import HybridRetriever
from app.rag.retrieval.pgvector_retriever import PGVectorRetriever

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="查询文本")
    top_k: int = Field(5, description="返回数量")
    score_threshold: float = Field(0.0, description="相似度阈值")
    use_hybrid: bool = Field(True, description="是否使用混合检索")


class FilteredSearchRequest(SearchRequest):
    """带过滤条件的搜索请求"""
    supplier: Optional[str] = Field(None, description="供应商名称")
    clause_type: Optional[str] = Field(None, description="条款类型")
    document_type: Optional[str] = Field(None, description="文档类型")
    section: Optional[str] = Field(None, description="章节")


@router.post("/projects/{project_id}")
async def search_in_project(
    project_id: int,
    request: FilteredSearchRequest,
    current_user: User = Depends(get_current_user),
):
    """在项目内搜索（支持元数据过滤）

    适用场景：
    - 投标文件项目，按供应商、条款类型过滤

    Example:
        POST /search/projects/1
        {
            "query": "报价明细",
            "supplier": "供应商A",
            "clause_type": "price_table"
        }
    """
    # 构建过滤条件
    filters = {}
    if request.supplier:
        filters["supplier"] = request.supplier
    if request.clause_type:
        filters["clause_type"] = request.clause_type
    if request.document_type:
        filters["document_type"] = request.document_type
    if request.section:
        filters["section"] = request.section

    # 选择检索器
    if request.use_hybrid:
        retriever = HybridRetriever(
            project_id=project_id,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
        )
    else:
        retriever = PGVectorRetriever(
            project_id=project_id,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
        )

    results = await retriever.search(
        request.query,
        filters=filters if filters else None
    )

    return {
        "query": request.query,
        "project_id": project_id,
        "filters": filters if filters else None,
        "search_type": "hybrid" if request.use_hybrid else "vector",
        "results_count": len(results),
        "results": results,
    }


@router.post("/projects/{project_id}/supplier/{supplier}")
async def search_by_supplier(
    project_id: int,
    supplier: str,
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
):
    """按供应商搜索

    快速定位特定供应商的相关信息。
    """
    retriever = HybridRetriever(
        project_id=project_id,
        top_k=request.top_k,
    )

    results = await retriever.search(
        request.query,
        filters={"supplier": supplier}
    )

    return {
        "query": request.query,
        "project_id": project_id,
        "supplier": supplier,
        "results_count": len(results),
        "results": results,
    }


@router.post("/projects/{project_id}/clause-type/{clause_type}")
async def search_by_clause_type(
    project_id: int,
    clause_type: str,
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
):
    """按条款类型搜索

    条款类型包括：
    - price_table: 报价表/价格条款
    - technical_clause: 技术条款
    - commercial_clause: 商务条款
    - legal_clause: 法律条款
    - qualification: 资质要求
    """
    retriever = HybridRetriever(
        project_id=project_id,
        top_k=request.top_k,
    )

    results = await retriever.search(
        request.query,
        filters={"clause_type": clause_type}
    )

    return {
        "query": request.query,
        "project_id": project_id,
        "clause_type": clause_type,
        "results_count": len(results),
        "results": results,
    }


@router.post("/global")
async def global_search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
):
    """全局搜索（跨所有项目）"""
    retriever = HybridRetriever(top_k=request.top_k)
    results = await retriever.search(request.query)

    return {
        "query": request.query,
        "results_count": len(results),
        "results": results,
    }


@router.post("/documents/{document_id}")
async def search_in_document(
    document_id: int,
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
):
    """在文档内搜索"""
    retriever = PGVectorRetriever()

    results = await retriever.search_by_document(
        document_id=document_id,
        query=request.query,
        top_k=request.top_k,
    )

    return {
        "query": request.query,
        "document_id": document_id,
        "results_count": len(results),
        "results": results,
    }