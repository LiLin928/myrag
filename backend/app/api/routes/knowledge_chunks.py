"""知识库分块管理 API"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.document import DocumentChunk, Document
from app.models.knowledge_base import KnowledgeBase
from app.dependencies import get_db
from app.schemas.chunk import (
    ChunkDetail,
    ChunkListResponse,
    ChunkMetadataUpdate,
    ChunkContentUpdate,
    ChunkMetadata,
    ChunkDetailWithMetadata,
    ChunkListWithMetadataResponse,
)
from app.schemas.metadata import MetadataResponse, MetadataUpdate, MetadataPatch

router = APIRouter(prefix="/knowledge", tags=["knowledge-chunks"])


@router.get(
    "/{knowledge_id}/documents/{document_id}/chunks",
    response_model=ChunkListWithMetadataResponse,
)
async def list_knowledge_document_chunks(
    knowledge_id: str = Path(..., description="知识库 ID"),
    document_id: str = Path(..., description="文档 ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    section_filter: Optional[str] = Query(None, description="章节过滤"),
    has_embedding: Optional[bool] = Query(None, description="是否有向量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取知识库文档分块列表（含继承元数据）"""

    # 验证知识库
    kb_result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id)
    )
    kb = kb_result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限操作此知识库")

    # 验证文档
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.knowledge_base_id == knowledge_id,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 获取文档元数据（用于继承）
    doc_metadata = document.doc_metadata or {}

    # 构建查询
    query = select(DocumentChunk).where(DocumentChunk.document_id == document_id)

    if section_filter:
        query = query.where(DocumentChunk.section_title == section_filter)

    if has_embedding is not None:
        if has_embedding:
            query = query.where(DocumentChunk.embedding_vector.isnot(None))
        else:
            query = query.where(DocumentChunk.embedding_vector.is_(None))

    # 计算总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页
    offset = (page - 1) * page_size
    query = (
        query.offset(offset)
        .limit(page_size)
        .order_by(DocumentChunk.page_number, DocumentChunk.clause_id)
    )

    result = await db.execute(query)
    chunks = result.scalars().all()

    # 构建响应（含继承元数据）
    chunk_details = []
    for chunk in chunks:
        own_metadata = chunk.user_metadata or {}
        merged = {**doc_metadata, **own_metadata}

        chunk_details.append(
            ChunkDetailWithMetadata(
                id=str(chunk.id),
                document_id=str(chunk.document_id),
                clause_id=chunk.clause_id,
                clause_type=chunk.clause_type,
                clause_title=chunk.clause_title,
                content=chunk.content,
                page_number=chunk.page_number or 1,
                content_length=chunk.content_length or len(chunk.content),
                metadata=MetadataResponse(
                    inherited=doc_metadata,
                    own=own_metadata,
                    merged=merged,
                ),
                has_embedding=chunk.embedding_vector is not None,
                created_at=chunk.created_at,
            )
        )

    return ChunkListWithMetadataResponse(
        total=total,
        page=page,
        page_size=page_size,
        chunks=chunk_details,
    )


@router.get("/projects/{project_id}/documents/{document_id}/chunks")
async def list_document_chunks(
    project_id: str = Path(..., description="项目 ID"),
    document_id: str = Path(..., description="文档 ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    section_filter: Optional[str] = Query(None, description="章节过滤"),
    has_embedding: Optional[bool] = Query(None, description="是否有向量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChunkListResponse:
    """获取文档分块列表"""

    # 验证文档所有权
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.project_id == project_id,
        )
    )
    document = doc_result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # 构建查询
    query = select(DocumentChunk).where(DocumentChunk.document_id == document_id)

    if section_filter:
        query = query.where(DocumentChunk.section_title == section_filter)

    if has_embedding is not None:
        if has_embedding:
            query = query.where(DocumentChunk.embedding_vector.isnot(None))
        else:
            query = query.where(DocumentChunk.embedding_vector.is_(None))

    # 计算总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(DocumentChunk.page_number, DocumentChunk.clause_id)

    result = await db.execute(query)
    chunks = result.scalars().all()

    # 构建响应
    chunk_details = []
    for chunk in chunks:
        metadata = ChunkMetadata(
            document_type=chunk.document_type,
            source_filename=chunk.source_filename,
            section_title=chunk.section_title,
            section_level=chunk.section_level,
            position_type=chunk.position_type,
            user_tags=chunk.user_metadata.get("user_tags", []) if chunk.user_metadata else [],
            category=chunk.user_metadata.get("category") if chunk.user_metadata else None,
            note=chunk.user_metadata.get("note") if chunk.user_metadata else None,
            custom_fields=chunk.user_metadata.get("custom_fields", {}) if chunk.user_metadata else {},
        )

        chunk_details.append(ChunkDetail(
            id=str(chunk.id),
            document_id=str(chunk.document_id),
            clause_id=chunk.clause_id,
            clause_type=chunk.clause_type,
            clause_title=chunk.clause_title,
            content=chunk.content,
            page_number=chunk.page_number or 1,
            content_length=chunk.content_length or len(chunk.content),
            metadata=metadata,
            has_embedding=chunk.embedding_vector is not None,
            created_at=chunk.created_at,
        ))

    return ChunkListResponse(
        total=total,
        page=page,
        page_size=page_size,
        chunks=chunk_details,
    )


@router.get("/chunks/{chunk_id}")
async def get_chunk_detail(
    chunk_id: str = Path(..., description="分块 ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChunkDetail:
    """获取单个分块详情"""

    result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.id == chunk_id)
    )
    chunk = result.scalar_one_or_none()

    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")

    metadata = ChunkMetadata(
        document_type=chunk.document_type,
        source_filename=chunk.source_filename,
        section_title=chunk.section_title,
        section_level=chunk.section_level,
        position_type=chunk.position_type,
        user_tags=chunk.user_metadata.get("user_tags", []) if chunk.user_metadata else [],
        category=chunk.user_metadata.get("category") if chunk.user_metadata else None,
        note=chunk.user_metadata.get("note") if chunk.user_metadata else None,
        custom_fields=chunk.user_metadata.get("custom_fields", {}) if chunk.user_metadata else {},
    )

    return ChunkDetail(
        id=str(chunk.id),
        document_id=str(chunk.document_id),
        clause_id=chunk.clause_id,
        clause_type=chunk.clause_type,
        clause_title=chunk.clause_title,
        content=chunk.content,
        page_number=chunk.page_number or 1,
        content_length=chunk.content_length or len(chunk.content),
        metadata=metadata,
        has_embedding=chunk.embedding_vector is not None,
        created_at=chunk.created_at,
    )


@router.get("/chunks/{chunk_id}/metadata", response_model=MetadataResponse)
async def get_chunk_metadata(
    chunk_id: str = Path(..., description="分块 ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取分块元数据（含继承的文档元数据）"""

    result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.id == chunk_id)
    )
    chunk = result.scalar_one_or_none()
    if not chunk:
        raise HTTPException(status_code=404, detail="分块不存在")

    # 获取文档元数据（继承）
    doc_result = await db.execute(
        select(Document).where(Document.id == chunk.document_id)
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 权限检查
    kb_result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == document.knowledge_base_id)
    )
    kb = kb_result.scalar_one_or_none()
    if not kb or kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限")

    inherited = document.doc_metadata or {}
    own = chunk.user_metadata or {}
    merged = {**inherited, **own}

    return MetadataResponse(
        inherited=inherited,
        own=own,
        merged=merged,
    )


@router.put("/chunks/{chunk_id}/metadata", response_model=MetadataResponse)
async def update_chunk_metadata_full(
    chunk_id: str = Path(..., description="分块 ID"),
    update_data: MetadataUpdate = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """全量更新分块自有元数据"""

    result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.id == chunk_id)
    )
    chunk = result.scalar_one_or_none()
    if not chunk:
        raise HTTPException(status_code=404, detail="分块不存在")

    # 获取文档元数据（用于检查冲突）
    doc_result = await db.execute(
        select(Document).where(Document.id == chunk.document_id)
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 权限检查
    kb_result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == document.knowledge_base_id)
    )
    kb = kb_result.scalar_one_or_none()
    if not kb or kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限")

    inherited = document.doc_metadata or {}

    # 检查与继承字段冲突
    for name in update_data.metadata:
        if name in inherited:
            raise HTTPException(
                status_code=400,
                detail=f"字段 '{name}' 已在文档元数据中存在，无法重复定义"
            )

    chunk.user_metadata = update_data.metadata
    await db.commit()
    await db.refresh(chunk)

    own = chunk.user_metadata or {}
    merged = {**inherited, **own}

    return MetadataResponse(
        inherited=inherited,
        own=own,
        merged=merged,
    )


@router.patch("/chunks/{chunk_id}/metadata", response_model=MetadataResponse)
async def patch_chunk_metadata(
    chunk_id: str = Path(..., description="分块 ID"),
    patch_data: MetadataPatch = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """增量更新分块自有元数据"""

    result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.id == chunk_id)
    )
    chunk = result.scalar_one_or_none()
    if not chunk:
        raise HTTPException(status_code=404, detail="分块不存在")

    # 获取文档元数据
    doc_result = await db.execute(
        select(Document).where(Document.id == chunk.document_id)
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 权限检查
    kb_result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == document.knowledge_base_id)
    )
    kb = kb_result.scalar_one_or_none()
    if not kb or kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限")

    inherited = document.doc_metadata or {}

    # 检查与继承字段冲突
    if patch_data.name in inherited:
        raise HTTPException(
            status_code=400,
            detail=f"字段 '{patch_data.name}' 已在文档元数据中存在，无法重复定义"
        )

    # 更新
    own = chunk.user_metadata or {}
    own[patch_data.name] = patch_data.value
    chunk.user_metadata = own

    await db.commit()
    await db.refresh(chunk)

    merged = {**inherited, **own}

    return MetadataResponse(
        inherited=inherited,
        own=own,
        merged=merged,
    )


@router.delete("/chunks/{chunk_id}/metadata/{field_name}")
async def delete_chunk_metadata_field(
    chunk_id: str = Path(..., description="分块 ID"),
    field_name: str = Path(..., description="字段名"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除分块自有元数据字段"""

    result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.id == chunk_id)
    )
    chunk = result.scalar_one_or_none()
    if not chunk:
        raise HTTPException(status_code=404, detail="分块不存在")

    # 权限检查
    doc_result = await db.execute(
        select(Document).where(Document.id == chunk.document_id)
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    kb_result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == document.knowledge_base_id)
    )
    kb = kb_result.scalar_one_or_none()
    if not kb or kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限")

    own = chunk.user_metadata or {}
    if field_name not in own:
        raise HTTPException(status_code=404, detail=f"字段 '{field_name}' 不存在")

    del own[field_name]
    chunk.user_metadata = own

    await db.commit()

    return {"deleted": field_name}


@router.put("/chunks/{chunk_id}/content")
async def update_chunk_content(
    chunk_id: str = Path(..., description="分块 ID"),
    update_data: ChunkContentUpdate = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """更新分块内容（触发重新向量化）"""

    result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.id == chunk_id)
    )
    chunk = result.scalar_one_or_none()

    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")

    # 更新内容
    chunk.content = update_data.content
    chunk.content_length = len(update_data.content)

    # 清除向量（需要重新生成）
    chunk.embedding_vector = None
    chunk.embedding_created_at = None

    await db.commit()
    await db.refresh(chunk)

    return {
        "id": str(chunk.id),
        "content_length": chunk.content_length,
        "needs_revectorization": True,
    }


@router.delete("/chunks/{chunk_id}")
async def delete_chunk(
    chunk_id: str = Path(..., description="分块 ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """删除分块（同时删除向量）"""

    result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.id == chunk_id)
    )
    chunk = result.scalar_one_or_none()

    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")

    # 更新文档统计
    doc_result = await db.execute(
        select(Document).where(Document.id == chunk.document_id)
    )
    document = doc_result.scalar_one_or_none()

    if document:
        document.chunk_count = max(0, document.chunk_count - 1)
        if chunk.embedding_vector:
            document.vectorized_count = max(0, document.vectorized_count - 1)

    await db.delete(chunk)
    await db.commit()

    return {"id": chunk_id, "deleted": True}


@router.post("/chunks/{chunk_id}/revectorize")
async def revectorize_chunk(
    chunk_id: str = Path(..., description="分块 ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """手动触发重新向量化"""

    result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.id == chunk_id)
    )
    chunk = result.scalar_one_or_none()

    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")

    # 提交向量化任务
    from app.tasks import get_redis_pool

    pool = await get_redis_pool()
    job = await pool.enqueue_job(
        "vectorize_single_chunk",
        str(chunk.id),
        str(current_user.id),
    )

    return {
        "chunk_id": str(chunk.id),
        "job_id": job.job_id,
        "status": "vectorizing",
    }