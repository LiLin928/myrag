"""分块业务服务

管理文档分块处理流程
"""

from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.models.document import Document, DocumentChunk, DocumentStatus
from app.rag.splitter.mixed_splitter import MixedSplitter

logger = logging.getLogger(__name__)


class ChunkService:
    """分块服务"""

    def __init__(self):
        self.splitter = MixedSplitter()

    async def process_document_chunks(
        self,
        db: AsyncSession,
        document: Document,
        parsed_data: Dict,
        strategy: str = "auto",
    ) -> List[DocumentChunk]:
        """处理文档分块

        Args:
            db: 数据库会话
            document: Document 实例
            parsed_data: 解析数据
            strategy: 分块策略

        Returns:
            DocumentChunk 列表
        """
        # 执行分块
        chunks_data = self.splitter.split(parsed_data, strategy)

        # DEBUG: 打印分块数据
        logger.info(f"=== ChunkService DEBUG ===")
        logger.info(f"parsed_data text length: {len(parsed_data.get('text', ''))}")
        logger.info(f"chunks_data from splitter: {len(chunks_data)}")

        # 获取文件类型字符串
        file_type_str = document.file_type.value if hasattr(document.file_type, 'value') else str(document.file_type)

        # 创建数据库记录
        db_chunks = []
        for chunk_data in chunks_data:
            db_chunk = DocumentChunk(
                document_id=str(document.id),
                project_id=document.project_id,
                knowledge_base_id=document.knowledge_base_id,  # 从文档获取知识库 ID
                clause_id=chunk_data.get("clause_id", f"chunk_{chunk_data.get('chunk_index', len(db_chunks))}"),  # 优先使用 chunk_data 的 clause_id
                clause_type=chunk_data.get("chunk_type", "paragraph"),
                clause_title=chunk_data.get("section_title"),
                content=chunk_data["content"],
                content_length=chunk_data.get("content_length", len(chunk_data["content"])),
                page_number=chunk_data.get("page_number", 1),

                # 三级元数据
                document_type=file_type_str,
                source_filename=document.filename,
                section_title=chunk_data.get("section_title"),
                section_level=chunk_data.get("section_level", 1),
                position_type=chunk_data.get("position_type", chunk_data.get("chunk_type", "body")),

                chunk_metadata={
                    "strategy": strategy,
                    "chunk_index": chunk_data.get("chunk_index", len(db_chunks)),
                },
            )
            db.add(db_chunk)
            db_chunks.append(db_chunk)
            logger.debug(f"Added chunk {len(db_chunks)}: {db_chunk.clause_id}, content_len={len(db_chunk.content)}")

        # 更新文档统计
        document.chunk_count = len(db_chunks)
        document.status = DocumentStatus.PARSED

        logger.info(f"About to commit {len(db_chunks)} chunks to database...")
        await db.commit()
        logger.info(f"Commit completed. Refreshing chunks...")

        # Refresh chunks to get IDs
        for chunk in db_chunks:
            await db.refresh(chunk)
            logger.debug(f"Refreshed chunk: id={chunk.id}, clause_id={chunk.clause_id}")

        logger.info(f"=== ChunkService COMPLETE ===")
        logger.info(f"Created {len(db_chunks)} chunks with IDs: {[str(c.id) for c in db_chunks[:3]]}")

        return db_chunks

    async def get_chunk_strategy_info(
        self,
        parsed_data: Dict,
    ) -> Dict[str, Any]:
        """获取分块策略信息

        Args:
            parsed_data: 解析数据

        Returns:
            策略信息
        """
        return self.splitter.get_strategy_info(parsed_data)

    async def delete_document_chunks(
        self,
        db: AsyncSession,
        document: Document,
    ) -> int:
        """删除文档所有分块

        Args:
            db: 数据库会话
            document: Document 实例

        Returns:
            删除数量
        """
        # 查询现有分块
        result = await db.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == str(document.id))
        )
        chunks = result.scalars().all()

        # 删除
        deleted_count = len(chunks)
        for chunk in chunks:
            await db.delete(chunk)

        # 更新文档统计
        document.chunk_count = 0
        document.vectorized_count = 0

        await db.commit()

        return deleted_count


# 全局服务实例
chunk_service = ChunkService()