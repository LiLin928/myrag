"""文档业务服务

处理文档上传、解析、状态管理等业务逻辑
"""

from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import Document, DocumentStatus, DocumentType
from app.services.file_service import get_file_service


class DocumentService:
    """文档服务"""

    async def create_document(
        self,
        db: AsyncSession,
        filename: str,
        file_content: bytes,
        user_id: str,
        project_id: Optional[str] = None,
    ) -> Document:
        """创建文档并上传文件

        Args:
            db: 数据库会话
            filename: 文件名
            file_content: 文件内容
            user_id: 用户 ID
            project_id: 项目 ID（可选）

        Returns:
            Document 实例
        """
        # 上传文件到 MinIO
        file_service = get_file_service()
        upload_result = await file_service.upload_file(
            content=file_content,
            filename=filename,
            user_id=user_id,
            project_id=project_id,
        )

        # 判断文件类型
        file_type = self._detect_file_type(filename)

        # 创建文档记录
        document = Document(
            filename=filename,
            file_path=upload_result["file_path"],
            file_type=file_type,
            file_size=upload_result["file_size"],
            user_id=user_id,
            project_id=project_id,
            status=DocumentStatus.PENDING,
        )

        db.add(document)
        await db.commit()
        await db.refresh(document)

        return document

    async def start_parsing(
        self,
        document: Document,
        user_id: str,
    ) -> Dict[str, Any]:
        """启动文档解析任务

        Args:
            document: Document 实例
            user_id: 用户 ID

        Returns:
            任务信息（包含 job_id）
        """
        from app.tasks import get_redis_pool

        # 获取 Redis 连接池
        pool = await get_redis_pool()

        # 提交 ARQ 任务
        job = await pool.enqueue_job(
            "parse_document",
            str(document.id),
            document.file_path,
            user_id,
        )

        # 更新文档状态
        document.status = DocumentStatus.PARSING
        document.processing_job_id = job.job_id

        return {
            "job_id": job.job_id,
            "document_id": str(document.id),
            "status": DocumentStatus.PARSING,
        }

    async def get_document(
        self,
        db: AsyncSession,
        document_id: str,
        user_id: str,
    ) -> Optional[Document]:
        """获取文档

        Args:
            db: 数据库会话
            document_id: 文档 ID
            user_id: 用户 ID

        Returns:
            Document 实例
        """
        result = await db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_documents(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: Optional[str] = None,
        status: Optional[DocumentStatus] = None,
    ) -> list[Document]:
        """列出文档

        Args:
            db: 数据库会话
            user_id: 用户 ID
            project_id: 项目 ID（可选）
            status: 状态过滤（可选）

        Returns:
            Document 列表
        """
        query = select(Document).where(Document.user_id == user_id)

        if project_id:
            query = query.where(Document.project_id == project_id)

        if status:
            query = query.where(Document.status == status)

        result = await db.execute(query)
        return result.scalars().all()

    def _detect_file_type(self, filename: str) -> DocumentType:
        """检测文件类型

        Args:
            filename: 文件名

        Returns:
            DocumentType
        """
        from pathlib import Path
        ext = Path(filename).suffix.lower()

        type_mapping = {
            ".pdf": DocumentType.PDF,
            ".doc": DocumentType.WORD,
            ".docx": DocumentType.WORD,
            ".md": DocumentType.MARKDOWN,
            ".markdown": DocumentType.MARKDOWN,
            ".txt": DocumentType.TEXT,
            ".html": DocumentType.HTML,
            ".htm": DocumentType.HTML,
            ".png": DocumentType.IMAGE,
            ".jpg": DocumentType.IMAGE,
            ".jpeg": DocumentType.IMAGE,
        }

        return type_mapping.get(ext, DocumentType.TEXT)


# 全局服务实例
document_service = DocumentService()