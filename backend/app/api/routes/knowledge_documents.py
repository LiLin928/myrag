"""知识库文档处理 API"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import uuid

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.knowledge_base import KnowledgeBase
from app.dependencies import get_db
from app.schemas.document import (
    DocumentStatusResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    ChunkStrategyEnum,
)
from app.schemas.metadata import MetadataResponse, MetadataUpdate, MetadataPatch, SYSTEM_METADATA_FIELDS
from app.services.document_service import document_service
from app.services.file_service import get_file_service

router = APIRouter(prefix="/knowledge", tags=["knowledge-documents"])

# 文件大小限制常量
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


# ============================================================
# 知识库文档管理 API
# ============================================================


@router.post("/{knowledge_id}/documents/upload")
async def upload_to_knowledge_base(
    knowledge_id: str = Path(..., description="知识库 ID"),
    file: UploadFile = File(..., description="上传的文件"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传文档到知识库

    Args:
        knowledge_id: 知识库 ID
        file: 上传的文件

    Returns:
        文档信息
    """
    # 验证 knowledge_id 格式
    try:
        kb_uuid = uuid.UUID(knowledge_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的知识库ID格式")

    # 验证知识库存在且用户有权限
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id)
    )
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    if kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限操作此知识库")

    # 读取文件内容
    content = await file.read()

    # 检查文件大小
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)"
        )

    # 检测文件类型
    file_type = document_service._detect_file_type(file.filename)

    # 创建文档记录（先不设置 file_path）
    document = Document(
        id=str(uuid.uuid4()),
        filename=file.filename,
        file_type=file_type.value,  # 存储枚举值字符串
        file_size=len(content),
        user_id=str(current_user.id),
        knowledge_base_id=knowledge_id,
        status=DocumentStatus.PENDING.value,  # 存储枚举值字符串
        # 继承知识库的分块和向量配置
        chunk_strategy=kb.chunk_strategy,
        chunk_size=kb.chunk_size,
        chunk_overlap=kb.chunk_overlap,
        embedding_model=kb.embedding_model,
        vector_dimension=kb.vector_dimension,
    )

    # 上传文件到 MinIO，包含事务回滚逻辑
    file_service = get_file_service()
    try:
        upload_result = await file_service.upload_file(
            content=content,
            filename=file.filename,
            user_id=str(current_user.id),
            knowledge_base_id=knowledge_id,
        )
        document.file_path = upload_result["file_path"]
        # 更新 file_size 为实际上传大小
        document.file_size = upload_result["file_size"]

        db.add(document)
        await db.commit()
        await db.refresh(document)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

    return {
        "id": str(document.id),
        "filename": document.filename,
        "file_type": document.file_type,  # 已经是字符串
        "file_size": document.file_size,
        "status": document.status,  # 已经是字符串
        "created_at": document.created_at,
    }


@router.get("/{knowledge_id}/documents")
async def list_knowledge_documents(
    knowledge_id: str = Path(..., description="知识库 ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出知识库文档

    Args:
        knowledge_id: 知识库 ID

    Returns:
        文档列表
    """
    # 验证 knowledge_id 格式
    try:
        kb_uuid = uuid.UUID(knowledge_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的知识库ID格式")

    # 验证知识库存在且用户有权限
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id)
    )
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    if kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限操作此知识库")

    # 查询文档列表
    result = await db.execute(
        select(Document)
        .where(Document.knowledge_base_id == knowledge_id)
        .order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()

    return [
        {
            "id": str(doc.id),
            "filename": doc.filename,
            "file_type": doc.file_type,  # 已经是字符串
            "file_size": doc.file_size,
            "status": doc.status,  # 已经是字符串
            "processing_progress": doc.processing_progress or 0,
            "processing_message": doc.processing_message,
            "chunk_count": doc.chunk_count or 0,
            "vectorized_count": doc.vectorized_count or 0,
            "created_at": doc.created_at,
        }
        for doc in documents
    ]


@router.post("/{knowledge_id}/documents/{document_id}/parse")
async def parse_knowledge_document(
    knowledge_id: str = Path(..., description="知识库 ID"),
    document_id: str = Path(..., description="文档 ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """解析知识库文档

    Args:
        knowledge_id: 知识库 ID
        document_id: 文档 ID

    Returns:
        任务信息
    """
    # 验证 knowledge_id 格式
    try:
        kb_uuid = uuid.UUID(knowledge_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的知识库ID格式")

    # 验证 document_id 格式
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的文档ID格式")

    # 验证知识库存在且用户有权限
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id)
    )
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    if kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限操作此知识库")

    # 验证文档存在且属于该知识库
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.knowledge_base_id == knowledge_id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 检查文档状态：只有 PENDING, FAILED, INDEXED 状态可以重新解析
    allowed_statuses = [DocumentStatus.PENDING.value, DocumentStatus.FAILED.value, DocumentStatus.INDEXED.value]
    if document.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"文档状态不允许解析 (当前状态: {document.status})"
        )

    # 提交 ARQ 任务
    from app.tasks import get_redis_pool

    pool = await get_redis_pool()
    job = await pool.enqueue_job(
        "parse_knowledge_document",
        str(document.id),
        str(current_user.id),
    )

    # 更新文档状态
    document.status = DocumentStatus.PARSING.value  # 存储字符串值
    document.processing_job_id = job.job_id
    document.processing_progress = 0
    document.processing_message = "等待解析"

    await db.commit()

    return {
        "job_id": job.job_id,
        "document_id": str(document.id),
        "status": document.status,  # 已经是字符串
        "websocket_channel": f"doc_processing_{document.id}",
    }


@router.delete("/{knowledge_id}/documents/{document_id}")
async def delete_knowledge_document(
    knowledge_id: str = Path(..., description="知识库 ID"),
    document_id: str = Path(..., description="文档 ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除知识库文档

    Args:
        knowledge_id: 知识库 ID
        document_id: 文档 ID

    Returns:
        删除确认信息
    """
    # 验证 knowledge_id 格式
    try:
        kb_uuid = uuid.UUID(knowledge_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的知识库ID格式")

    # 验证 document_id 格式
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的文档ID格式")

    # 验证知识库存在且用户有权限
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id)
    )
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    if kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限操作此知识库")

    # 验证文档存在且属于该知识库
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.knowledge_base_id == knowledge_id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 删除文档（级联删除会处理 chunks）
    deleted_id = str(document.id)
    await db.delete(document)
    await db.commit()

    return {"deleted": deleted_id}


# ============================================================
# 文档元数据管理 API
# ============================================================


@router.get("/{knowledge_id}/documents/{document_id}/metadata", response_model=MetadataResponse)
async def get_document_metadata(
    knowledge_id: str = Path(..., description="知识库 ID"),
    document_id: str = Path(..., description="文档 ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取文档元数据"""

    # 验证权限
    kb_result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id)
    )
    kb = kb_result.scalar_one_or_none()
    if not kb or kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限")

    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.knowledge_base_id == knowledge_id,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    metadata = document.doc_metadata or {}

    return MetadataResponse(
        inherited={},  # 文档没有继承
        own=metadata,
        merged=metadata,
    )


@router.put("/{knowledge_id}/documents/{document_id}/metadata", response_model=MetadataResponse)
async def update_document_metadata(
    knowledge_id: str = Path(..., description="知识库 ID"),
    document_id: str = Path(..., description="文档 ID"),
    update_data: MetadataUpdate = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """全量更新文档元数据"""

    # 验证权限
    kb_result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id)
    )
    kb = kb_result.scalar_one_or_none()
    if not kb or kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限")

    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.knowledge_base_id == knowledge_id,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 检查与系统预定义只读字段冲突
    readonly_fields = {f["name"] for f in SYSTEM_METADATA_FIELDS if f["readonly"]}
    for name in update_data.metadata:
        if name in readonly_fields:
            raise HTTPException(
                status_code=400,
                detail=f"字段 '{name}' 是系统只读字段，无法修改"
            )

    # 保留系统预定义只读字段，更新其他字段
    current_metadata = document.doc_metadata or {}
    new_metadata = {}

    # 保留只读系统字段
    for name in readonly_fields:
        if name in current_metadata:
            new_metadata[name] = current_metadata[name]

    # 合并用户更新
    new_metadata.update(update_data.metadata)

    document.doc_metadata = new_metadata
    await db.commit()
    await db.refresh(document)

    return MetadataResponse(
        inherited={},
        own=new_metadata,
        merged=new_metadata,
    )


@router.patch("/{knowledge_id}/documents/{document_id}/metadata", response_model=MetadataResponse)
async def patch_document_metadata(
    knowledge_id: str = Path(..., description="知识库 ID"),
    document_id: str = Path(..., description="文档 ID"),
    patch_data: MetadataPatch = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """增量更新文档元数据（添加或修改单个字段）"""

    # 验证权限
    kb_result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id)
    )
    kb = kb_result.scalar_one_or_none()
    if not kb or kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限")

    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.knowledge_base_id == knowledge_id,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 检查只读字段
    readonly_fields = {f["name"] for f in SYSTEM_METADATA_FIELDS if f["readonly"]}
    if patch_data.name in readonly_fields:
        raise HTTPException(
            status_code=400,
            detail=f"字段 '{patch_data.name}' 是系统只读字段，无法修改"
        )

    # 更新
    current_metadata = document.doc_metadata or {}
    current_metadata[patch_data.name] = patch_data.value
    document.doc_metadata = current_metadata

    await db.commit()
    await db.refresh(document)

    return MetadataResponse(
        inherited={},
        own=current_metadata,
        merged=current_metadata,
    )


@router.delete("/{knowledge_id}/documents/{document_id}/metadata/{field_name}")
async def delete_document_metadata_field(
    knowledge_id: str = Path(..., description="知识库 ID"),
    document_id: str = Path(..., description="文档 ID"),
    field_name: str = Path(..., description="字段名"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除文档元数据字段"""

    # 验证权限
    kb_result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id)
    )
    kb = kb_result.scalar_one_or_none()
    if not kb or kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限")

    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.knowledge_base_id == knowledge_id,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 检查只读字段
    readonly_fields = {f["name"] for f in SYSTEM_METADATA_FIELDS if f["readonly"]}
    if field_name in readonly_fields:
        raise HTTPException(
            status_code=400,
            detail=f"字段 '{field_name}' 是系统只读字段，无法删除"
        )

    # 删除字段
    current_metadata = document.doc_metadata or {}
    if field_name not in current_metadata:
        raise HTTPException(status_code=404, detail=f"字段 '{field_name}' 不存在")

    del current_metadata[field_name]
    document.doc_metadata = current_metadata

    await db.commit()

    return {"deleted": field_name}


# ============================================================
# 项目文档 API（保留原有接口）
# ============================================================


@router.get("/projects/{project_id}/documents/{document_id}/status")
async def get_document_status(
    project_id: str = Path(..., description="项目 ID"),
    document_id: str = Path(..., description="文档 ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentStatusResponse:
    """获取文档处理状态"""
    # 验证 project_id 格式
    try:
        uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的项目ID格式")

    # 验证 document_id 格式
    try:
        uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的文档ID格式")

    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.project_id == project_id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentStatusResponse(
        document_id=str(document.id),
        status=document.status,
        progress=document.processing_progress or 0,
        message=document.processing_message,
        chunk_count=document.chunk_count or 0,
        vectorized_count=document.vectorized_count or 0,
        websocket_channel=f"doc_processing_{document.id}",
    )


@router.get("/projects/{project_id}/documents")
async def list_project_documents(
    project_id: str = Path(..., description="项目 ID"),
    status: Optional[str] = Query(None, description="状态过滤"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentListResponse:
    """列出项目文档"""
    # 验证 project_id 格式
    try:
        uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的项目ID格式")

    query = select(Document).where(Document.project_id == project_id)

    if status:
        query = query.where(Document.status == status)

    result = await db.execute(query)
    documents = result.scalars().all()

    doc_details = [
        DocumentDetailResponse(
            id=str(doc.id),
            filename=doc.filename,
            file_type=doc.file_type.value if hasattr(doc.file_type, 'value') else str(doc.file_type),
            file_size=doc.file_size,
            status=doc.status,
            chunk_strategy=doc.chunk_strategy or "auto",
            chunk_count=doc.chunk_count or 0,
            vectorized_count=doc.vectorized_count or 0,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            processed_at=doc.processed_at,
        )
        for doc in documents
    ]

    return DocumentListResponse(
        total=len(documents),
        documents=doc_details,
    )


@router.post("/projects/{project_id}/documents/{document_id}/reprocess")
async def reprocess_document(
    project_id: str = Path(..., description="项目 ID"),
    document_id: str = Path(..., description="文档 ID"),
    chunk_strategy: ChunkStrategyEnum = Query(ChunkStrategyEnum.AUTO, description="分块策略"),
    enable_vectorization: bool = Query(True, description="是否向量化"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """重新处理文档"""
    # 验证 project_id 格式
    try:
        uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的项目ID格式")

    # 验证 document_id 格式
    try:
        uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的文档ID格式")

    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.project_id == project_id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # 重置状态
    document.status = DocumentStatus.PENDING
    document.processing_progress = 0
    document.processing_message = "等待处理"
    document.chunk_strategy = chunk_strategy.value
    document.enable_vectorization = enable_vectorization

    await db.commit()

    # 提交处理任务
    from app.tasks import get_redis_pool

    pool = await get_redis_pool()
    job = await pool.enqueue_job(
        "process_document_full",
        str(document.id),
        str(current_user.id),
    )

    return {
        "document_id": str(document.id),
        "job_id": job.job_id,
        "status": "processing",
        "websocket_channel": f"doc_processing_{document.id}",
    }