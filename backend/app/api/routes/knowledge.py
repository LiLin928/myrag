"""知识库 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import datetime
import uuid

from pydantic import BaseModel, Field

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.models.model_config import ModelConfig
from app.services.model_service import ModelService
from app.db import get_db

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# 请求/响应模型
class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

    # 分块配置
    chunk_strategy: str = Field(default="auto", description="分块策略: auto/structured/semantic/fixed")
    chunk_size: int = Field(default=800, ge=100, le=2000, description="分块大小")
    chunk_overlap: int = Field(default=100, ge=0, le=500, description="分块重叠")

    # 向量配置
    embedding_model: str = Field(default="text-embedding-3-small", description="向量模型")

    # Rerank 配置
    rerank_model: Optional[str] = Field(default=None, description="Rerank模型")
    rerank_enabled: bool = Field(default=False, description="是否启用Rerank")
    rerank_top_n: int = Field(default=10, ge=5, le=50, description="Rerank前取多少条")

    # 检索配置
    retrieval_method: str = Field(default="hybrid", description="检索方法: vector/keyword/hybrid")
    retrieval_top_k: int = Field(default=10, ge=1, le=100, description="返回数量")
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="相似度阈值")

    # 混合检索权重
    vector_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="向量权重")
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="关键词权重")


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

    # 分块配置
    chunk_strategy: Optional[str] = Field(None, description="分块策略: auto/structured/semantic/fixed")
    chunk_size: Optional[int] = Field(None, ge=100, le=2000, description="分块大小")
    chunk_overlap: Optional[int] = Field(None, ge=0, le=500, description="分块重叠")

    # 向量配置
    embedding_model: Optional[str] = Field(None, description="向量模型")

    # Rerank 配置
    rerank_model: Optional[str] = Field(None, description="Rerank模型")
    rerank_enabled: Optional[bool] = Field(None, description="是否启用Rerank")
    rerank_top_n: Optional[int] = Field(None, ge=5, le=50, description="Rerank前取多少条")

    # 检索配置
    retrieval_method: Optional[str] = Field(None, description="检索方法: vector/keyword/hybrid")
    retrieval_top_k: Optional[int] = Field(None, ge=1, le=100, description="返回数量")
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="相似度阈值")

    # 混合检索权重
    vector_weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="向量权重")
    keyword_weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="关键词权重")


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""
    id: str
    name: str
    description: Optional[str]
    document_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    # 分块配置
    chunk_strategy: str
    chunk_size: int
    chunk_overlap: int

    # 向量配置
    embedding_model: str
    vector_dimension: int

    # Rerank 配置
    rerank_model: Optional[str]
    rerank_enabled: bool
    rerank_top_n: int

    # 检索配置
    retrieval_method: str
    retrieval_top_k: int
    similarity_threshold: float
    vector_weight: float
    keyword_weight: float

    class Config:
        from_attributes = True


class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应"""
    items: List[KnowledgeBaseResponse]
    total: int


def kb_to_response(kb: KnowledgeBase) -> KnowledgeBaseResponse:
    """将 KnowledgeBase 模型转换为响应模型"""
    return KnowledgeBaseResponse(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        document_count=kb.document_count,
        created_at=kb.created_at,
        updated_at=kb.updated_at,
        chunk_strategy=kb.chunk_strategy,
        chunk_size=kb.chunk_size,
        chunk_overlap=kb.chunk_overlap,
        embedding_model=kb.embedding_model,
        vector_dimension=kb.vector_dimension,
        rerank_model=kb.rerank_model,
        rerank_enabled=kb.rerank_enabled,
        rerank_top_n=kb.rerank_top_n,
        retrieval_method=kb.retrieval_method,
        retrieval_top_k=kb.retrieval_top_k,
        similarity_threshold=kb.similarity_threshold,
        vector_weight=kb.vector_weight,
        keyword_weight=kb.keyword_weight,
    )


@router.get("/", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取知识库列表"""
    # 查询总数
    count_query = select(func.count()).select_from(KnowledgeBase)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 查询列表
    query = select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    knowledge_bases = result.scalars().all()

    return KnowledgeBaseListResponse(
        items=[kb_to_response(kb) for kb in knowledge_bases],
        total=total,
    )


@router.post("/", response_model=KnowledgeBaseResponse, status_code=201)
async def create_knowledge_base(
    request: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建知识库"""
    print(f"创建知识库请求: {request.model_dump()}")

    model_service = ModelService(db)

    # 获取 embedding 模型配置
    embedding_model_name = request.embedding_model
    vector_dimension = 1536  # 默认维度

    # 如果 embedding_model 是 UUID 格式，则查找模型配置
    try:
        uuid.UUID(request.embedding_model)
        embedding_config = await model_service.get_model(request.embedding_model)
        if embedding_config and embedding_config.type == 'embedding':
            embedding_model_name = embedding_config.model_name
            vector_dimension = embedding_config.dimension or 1536
    except ValueError:
        # 不是 UUID，直接使用字符串作为模型名称
        pass

    # 获取 rerank 模型配置
    rerank_model_name = request.rerank_model
    if request.rerank_enabled and request.rerank_model:
        try:
            uuid.UUID(request.rerank_model)
            rerank_config = await model_service.get_model(request.rerank_model)
            if rerank_config and rerank_config.type == 'rerank':
                rerank_model_name = rerank_config.model_name
        except ValueError:
            pass

    knowledge_base = KnowledgeBase(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        # 分块配置
        chunk_strategy=request.chunk_strategy,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
        # 向量配置
        embedding_model=embedding_model_name,
        vector_dimension=vector_dimension,
        # Rerank 配置
        rerank_model=rerank_model_name,
        rerank_enabled=request.rerank_enabled,
        rerank_top_n=request.rerank_top_n,
        # 检索配置
        retrieval_method=request.retrieval_method,
        retrieval_top_k=request.retrieval_top_k,
        similarity_threshold=request.similarity_threshold,
        vector_weight=request.vector_weight,
        keyword_weight=request.keyword_weight,
    )
    db.add(knowledge_base)
    await db.commit()
    await db.refresh(knowledge_base)

    return kb_to_response(knowledge_base)


@router.get("/{knowledge_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    knowledge_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个知识库"""
    query = select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id)
    result = await db.execute(query)
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 权限验证
    if kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限操作此知识库")

    return kb_to_response(kb)


@router.put("/{knowledge_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    knowledge_id: str,
    request: KnowledgeBaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新知识库"""
    query = select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id)
    result = await db.execute(query)
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 权限验证
    if kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限操作此知识库")

    # 更新基础字段
    if request.name is not None:
        kb.name = request.name
    if request.description is not None:
        kb.description = request.description

    # 更新分块配置
    if request.chunk_strategy is not None:
        kb.chunk_strategy = request.chunk_strategy
    if request.chunk_size is not None:
        kb.chunk_size = request.chunk_size
    if request.chunk_overlap is not None:
        kb.chunk_overlap = request.chunk_overlap

    # 更新向量配置
    if request.embedding_model is not None:
        kb.embedding_model = request.embedding_model

    # 更新 Rerank 配置
    if request.rerank_model is not None:
        kb.rerank_model = request.rerank_model
    if request.rerank_enabled is not None:
        kb.rerank_enabled = request.rerank_enabled
    if request.rerank_top_n is not None:
        kb.rerank_top_n = request.rerank_top_n

    # 更新检索配置
    if request.retrieval_method is not None:
        kb.retrieval_method = request.retrieval_method
    if request.retrieval_top_k is not None:
        kb.retrieval_top_k = request.retrieval_top_k
    if request.similarity_threshold is not None:
        kb.similarity_threshold = request.similarity_threshold
    if request.vector_weight is not None:
        kb.vector_weight = request.vector_weight
    if request.keyword_weight is not None:
        kb.keyword_weight = request.keyword_weight

    kb.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(kb)

    return kb_to_response(kb)


@router.delete("/{knowledge_id}")
async def delete_knowledge_base(
    knowledge_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除知识库"""
    query = select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id)
    result = await db.execute(query)
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 权限验证
    if kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限操作此知识库")

    await db.delete(kb)
    await db.commit()

    return {"message": "删除成功"}


# 原有的项目文档接口保留
@router.get("/projects/{project_id}/documents")
async def list_project_documents(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出项目下的文档"""
    from app.models.document import Document

    query = select(Document).where(Document.project_id == project_id)
    result = await db.execute(query)
    documents = result.scalars().all()

    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "status": doc.status,
            "created_at": doc.created_at,
        }
        for doc in documents
    ]


@router.get("/projects/{project_id}/stats")
async def get_project_stats(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目统计信息"""
    from sqlalchemy import text
    from app.models.document import Document

    doc_result = await db.execute(
        select(Document).where(Document.project_id == project_id)
    )
    documents = doc_result.scalars().all()

    chunks_result = await db.execute(
        text("""
            SELECT COUNT(*) as total,
                   COUNT(embedding_vector) as vectorized
            FROM document_chunks
            WHERE project_id = :project_id
        """),
        {"project_id": project_id}
    )
    chunks_stats = chunks_result.fetchone()

    return {
        "project_id": project_id,
        "document_count": len(documents),
        "chunk_total": chunks_stats[0] if chunks_stats else 0,
        "chunk_vectorized": chunks_stats[1] if chunks_stats else 0,
    }