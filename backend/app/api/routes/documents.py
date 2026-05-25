"""文档 API 路由"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.document import DocumentStatus
from app.services.document_service import document_service
from app.dependencies import get_db

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    project_id: str = Query(None, description="项目 ID"),
    auto_parse: bool = Query(True, description="自动启动解析"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传文档

    Args:
        file: 上传的文件
        project_id: 关联项目 ID（可选）
        auto_parse: 是否自动启动解析

    Returns:
        文档信息和任务 ID
    """
    # 读取文件内容
    content = await file.read()

    # 创建文档
    document = await document_service.create_document(
        db=db,
        filename=file.filename,
        file_content=content,
        user_id=str(current_user.id),
        project_id=project_id,
    )

    # 自动启动解析
    if auto_parse:
        job_info = await document_service.start_parsing(document, str(current_user.id))
        await db.commit()  # 更新状态后提交

        return {
            "document": {
                "id": str(document.id),
                "filename": document.filename,
                "status": document.status,
            },
            "job": job_info,
        }

    return {
        "document": {
            "id": str(document.id),
            "filename": document.filename,
            "status": document.status,
        }
    }


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取文档详情

    Args:
        document_id: 文档 ID

    Returns:
        文档信息
    """
    document = await document_service.get_document(
        db=db,
        document_id=document_id,
        user_id=str(current_user.id),
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": str(document.id),
        "filename": document.filename,
        "file_type": document.file_type,
        "file_size": document.file_size,
        "status": document.status,
        "processing_job_id": document.processing_job_id,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


@router.get("/")
async def list_documents(
    project_id: str = Query(None),
    status: DocumentStatus = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出文档

    Args:
        project_id: 项目 ID 过滤
        status: 状态过滤

    Returns:
        文档列表
    """
    documents = await document_service.list_documents(
        db=db,
        user_id=str(current_user.id),
        project_id=project_id,
        status=status,
    )

    return [
        {
            "id": str(doc.id),
            "filename": doc.filename,
            "file_type": doc.file_type,
            "status": doc.status,
            "created_at": doc.created_at,
        }
        for doc in documents
    ]


@router.post("/{document_id}/parse")
async def start_parse(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """启动文档解析

    Args:
        document_id: 文档 ID

    Returns:
        任务信息
    """
    document = await document_service.get_document(
        db=db,
        document_id=document_id,
        user_id=str(current_user.id),
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.status != DocumentStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Document already processing or processed (status: {document.status})"
        )

    job_info = await document_service.start_parsing(document, str(current_user.id))
    await db.commit()

    return job_info