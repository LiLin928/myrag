"""文档解析 ARQ 任务

后台执行耗时的文档处理：
- 文档解析
- 分块处理
- 向量化
- 完整处理流水线
- 知识库文档处理
"""

from typing import Dict, Any, List
import asyncio
import os
from datetime import datetime
from pathlib import Path
import json
import logging

from app.rag.extractor.factory import ExtractorFactory
from app.rag.splitter.mixed_splitter import MixedSplitter
from app.rag.embedding.embedding_service import get_embedding_service_for_task, get_embedding_service
from app.services.chunk_service import ChunkService
from app.tasks.progress_tracker import (
    track_progress,
    notify_task_complete,
    notify_task_failed,
)
from app.models.document import DocumentStatus, Document, DocumentChunk

logger = logging.getLogger(__name__)


async def parse_document(
    ctx: dict,
    document_id: str,
    file_path: str,
    user_id: str,
) -> Dict[str, Any]:
    """解析文档（ARQ 任务）

    Args:
        ctx: ARQ 任务上下文
        document_id: 文档 ID
        file_path: MinIO 文件路径
        user_id: 用户 ID

    Returns:
        解析结果
    """
    job_id = ctx["job_id"]

    # 开始解析
    await track_progress(job_id, user_id, "parsing", 0, "开始解析文档")

    try:
        # 获取解析器
        extractor = ExtractorFactory.get_extractor(file_path)

        if not extractor:
            await notify_task_failed(job_id, user_id, "Unsupported file type")
            return {"status": "failed", "error": "Unsupported file type"}

        # 执行解析
        await track_progress(job_id, user_id, "parsing", 30, "正在解析...")

        # 使用模拟数据（实际应从文件解析）
        blocks = await extractor.extract(file_path)

        await track_progress(job_id, user_id, "parsing", 80, "解析完成，保存结果")

        result = {
            "status": "completed",
            "document_id": document_id,
            "content_blocks": blocks,
            "blocks_count": len(blocks),
        }

        await notify_task_complete(job_id, user_id, result)

        return result

    except Exception as e:
        await notify_task_failed(job_id, user_id, str(e))
        return {"status": "failed", "error": str(e)}


async def chunk_document(
    ctx: dict,
    document_id: str,
    parsed_data: Dict,
    strategy: str = "auto",
    user_id: str = None,
) -> Dict[str, Any]:
    """分块处理（ARQ 任务）

    Args:
        ctx: ARQ 任务上下文
        document_id: 文档 ID
        parsed_data: 解析数据
        strategy: 分块策略
        user_id: 用户 ID

    Returns:
        分块结果
    """
    job_id = ctx["job_id"]

    await track_progress(job_id, user_id, "chunking", 0, "开始分块处理")

    try:
        # 使用混合分块器
        splitter = MixedSplitter()
        chunks = splitter.split(parsed_data, strategy)

        await track_progress(job_id, user_id, "chunking", 50, f"已生成 {len(chunks)} 个分块")

        result = {
            "status": "completed",
            "document_id": document_id,
            "chunks": chunks,
            "chunk_count": len(chunks),
            "strategy": strategy,
        }

        await notify_task_complete(job_id, user_id, result)

        return result

    except Exception as e:
        await notify_task_failed(job_id, user_id, str(e))
        return {"status": "failed", "error": str(e)}


async def vectorize_chunks(
    ctx: dict,
    document_id: str,
    chunks: List[Dict],
    user_id: str,
    project_id: str = None,
) -> Dict[str, Any]:
    """批量向量化（ARQ 任务）

    Args:
        ctx: ARQ 任务上下文
        document_id: 文档 ID
        chunks: 分块列表（包含 content, clause_id, clause_type 等）
        user_id: 用户 ID
        project_id: 项目 ID（可选）

    Returns:
        向量化结果
    """
    job_id = ctx["job_id"]

    await track_progress(job_id, user_id, "vectorizing", 0, "开始向量化")

    from app.dependencies import get_db
    from sqlalchemy import text
    import json

    # 获取知识库的 embedding_model 配置
    embedding_model = None
    async for db in get_db():
        # 查询文档关联的知识库
        kb_query = text("""
            SELECT kb.embedding_model, kb.id, kb.vector_dimension
            FROM documents d
            LEFT JOIN knowledge_bases kb ON d.knowledge_base_id = kb.id
            WHERE d.id = :document_id
        """)
        result = await db.execute(kb_query, {"document_id": document_id})
        kb_row = result.fetchone()

        if kb_row:
            embedding_model = kb_row[0]  # kb.embedding_model
            kb_id = kb_row[1]
            kb_dimension = kb_row[2]
            logger.info(f"Using KB embedding_model: {embedding_model}, dimension: {kb_dimension}")
        else:
            # 使用默认配置（将从数据库系统设置获取）
            embedding_model = None
            logger.info(f"No KB config, will use default from system settings")

        break  # 只需要获取一次配置

    # 从数据库系统设置获取 embedding 服务
    embedding_service = await get_embedding_service_for_task(model_name=embedding_model)
    # 获取实际使用的模型名称
    actual_model_name = embedding_service.config.model_name
    logger.info(f"Embedding service created with model: {actual_model_name}")

    total = len(chunks)
    vectorized_count = 0

    # 批量处理（每批 50 条）
    batch_size = 50

    try:
        # 获取文本内容
        texts = [chunk.get("content", "") for chunk in chunks]

        # 分批嵌入
        all_embeddings = []
        for start in range(0, total, batch_size):
            batch_texts = texts[start:start + batch_size]

            embeddings = await embedding_service.embed_batch(batch_texts)
            all_embeddings.extend(embeddings)

            vectorized_count = min(start + batch_size, total)
            progress = int((vectorized_count / total) * 100)

            await track_progress(
                job_id, user_id, "vectorizing", progress,
                f"已处理 {vectorized_count}/{total} 条 (模型: {actual_model_name})"
            )

        # 存储向量到数据库
        await track_progress(job_id, user_id, "storing", 0, "开始存储向量")

        async for db in get_db():
            for i, (chunk, embedding) in enumerate(zip(chunks, all_embeddings)):
                chunk_id = chunk.get("id") or chunk.get("clause_id")

                # 更新向量
                embedding_str = json.dumps(embedding)

                query = text("""
                    UPDATE document_chunks
                    SET embedding_vector = :embedding::vector,
                        embedding_model = :embedding_model,
                        embedding_created_at = NOW()
                    WHERE clause_id = :clause_id AND document_id = :document_id
                """)

                await db.execute(query, {
                    "clause_id": chunk_id,
                    "document_id": document_id,
                    "embedding": embedding_str,
                    "embedding_model": actual_model_name,  # 使用实际配置的模型
                })

            # 更新文档统计
            doc_query = text("""
                UPDATE documents
                SET vectorized_count = :count,
                    status = :status,
                    updated_at = NOW()
                WHERE id = :document_id
            """)

            await db.execute(doc_query, {
                "document_id": document_id,
                "count": total,
                "status": DocumentStatus.INDEXED.value,
            })

            await db.commit()

        await track_progress(job_id, user_id, "storing", 100, "向量存储完成")

        result = {
            "status": "completed",
            "document_id": document_id,
            "chunk_count": total,
            "vectorized_count": total,
        }

        await notify_task_complete(job_id, user_id, result)

        return result

    except Exception as e:
        await notify_task_failed(job_id, user_id, str(e))
        return {"status": "failed", "error": str(e)}


async def process_document_full(
    ctx: dict,
    document_id: str,
    user_id: str,
    chunk_strategy: str = "auto",
    enable_vectorization: bool = True,
) -> Dict[str, Any]:
    """完整文档处理流水线（ARQ 任务）

    流程：解析 → 分块 → 向量化 → 存储

    Args:
        ctx: ARQ 任务上下文
        document_id: 文档 ID
        user_id: 用户 ID
        chunk_strategy: 分块策略
        enable_vectorization: 是否启用向量化

    Returns:
        处理结果
    """
    job_id = ctx["job_id"]

    from app.dependencies import get_db
    from app.models.document import Document
    from sqlalchemy import select

    try:
        # 获取文档
        async for db in get_db():
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()

            if not document:
                await notify_task_failed(job_id, user_id, "Document not found")
                return {"status": "failed", "error": "Document not found"}

            # 更新状态为处理中
            document.status = DocumentStatus.PARSING
            document.processing_progress = 0
            document.processing_message = "开始处理"
            await db.commit()

            file_path = document.file_path

        # Step 1: 解析文档 (10% - 30%)
        await track_progress(job_id, user_id, "parsing", 10, "开始解析文档")

        # 使用模拟解析数据（实际应调用真实解析器）
        parsed_data = {
            "text": "模拟文档内容...",
            "sections": [],
            "tables": [],
        }

        await track_progress(job_id, user_id, "parsing", 30, "解析完成")

        # Step 2: 分块处理 (40% - 60%)
        await track_progress(job_id, user_id, "chunking", 40, "开始分块处理")

        splitter = MixedSplitter()
        chunks = splitter.split(parsed_data, chunk_strategy)

        await track_progress(job_id, user_id, "chunking", 60, f"已生成 {len(chunks)} 个分块")

        # 存储分块到数据库
        async for db in get_db():
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()

            chunk_service = ChunkService()
            await chunk_service.process_document_chunks(db, document, parsed_data, chunk_strategy)

            # 更新状态
            document.status = DocumentStatus.PARSED
            document.processing_progress = 60
            document.processing_message = f"已分块 {len(chunks)} 条"
            await db.commit()

        # Step 3: 向量化 (70% - 90%)
        if enable_vectorization and len(chunks) > 0:
            await track_progress(job_id, user_id, "vectorizing", 70, "开始向量化")

            await vectorize_chunks(ctx, document_id, chunks, user_id)

            async for db in get_db():
                result = await db.execute(
                    select(Document).where(Document.id == document_id)
                )
                document = result.scalar_one_or_none()

                document.status = DocumentStatus.INDEXED
                document.processing_progress = 100
                document.processing_message = "处理完成"
                await db.commit()

        else:
            # 不向量化，直接完成
            async for db in get_db():
                result = await db.execute(
                    select(Document).where(Document.id == document_id)
                )
                document = result.scalar_one_or_none()

                document.status = DocumentStatus.PARSED
                document.processing_progress = 100
                document.processing_message = "处理完成（未向量化）"
                await db.commit()

        # 完成
        result = {
            "status": "completed",
            "document_id": document_id,
            "chunk_count": len(chunks),
            "vectorized": enable_vectorization,
        }

        await notify_task_complete(job_id, user_id, result)

        return result

    except Exception as e:
        # 更新文档状态为失败
        async for db in get_db():
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()

            if document:
                document.status = DocumentStatus.FAILED
                document.processing_message = str(e)
                await db.commit()

        await notify_task_failed(job_id, user_id, str(e))
        return {"status": "failed", "error": str(e)}


async def vectorize_single_chunk(
    ctx: dict,
    chunk_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """向量化单个分块（ARQ 任务）

    Args:
        ctx: ARQ 任务上下文
        chunk_id: 分块 ID
        user_id: 用户 ID

    Returns:
        向量化结果
    """
    job_id = ctx["job_id"]

    from app.dependencies import get_db
    from app.models.document import DocumentChunk
    from sqlalchemy import select, text
    import json

    await track_progress(job_id, user_id, "vectorizing", 0, "开始向量化单个分块")

    try:
        async for db in get_db():
            # 获取分块
            result = await db.execute(
                select(DocumentChunk).where(DocumentChunk.id == chunk_id)
            )
            chunk = result.scalar_one_or_none()

            if not chunk:
                await notify_task_failed(job_id, user_id, "Chunk not found")
                return {"status": "failed", "error": "Chunk not found"}

            # 嵌入
            embedding_service = get_embedding_service()
            embedding = await embedding_service.embed_text(chunk.content)

            # 更新向量
            embedding_str = json.dumps(embedding)

            query = text("""
                UPDATE document_chunks
                SET embedding_vector = :embedding::vector,
                    embedding_model = :embedding_model,
                    embedding_created_at = NOW()
                WHERE id = :chunk_id
            """)

            await db.execute(query, {
                "chunk_id": chunk_id,
                "embedding": embedding_str,
                "embedding_model": "text-embedding-3-small",
            })

            await db.commit()

        await track_progress(job_id, user_id, "vectorizing", 100, "向量化完成")

        result = {
            "status": "completed",
            "chunk_id": chunk_id,
        }

        await notify_task_complete(job_id, user_id, result)

        return result

    except Exception as e:
        await notify_task_failed(job_id, user_id, str(e))
        return {"status": "failed", "error": str(e)}


async def parse_knowledge_document(
    ctx: dict,
    document_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """知识库文档解析任务（ARQ 任务）

    支持 MinerU 解析 → 分块 → 向量化完整流程。
    使用知识库配置进行分块和向量化。

    Args:
        ctx: ARQ 任务上下文
        document_id: 文档 ID
        user_id: 用户 ID

    Returns:
        处理结果
    """
    job_id = ctx["job_id"]

    from app.dependencies import get_db_session
    from app.models.knowledge_base import KnowledgeBase
    from sqlalchemy import select, text, delete

    db = None
    chunks_created = []  # Track created chunk IDs for cleanup on failure

    try:
        # Step 1: 获取文档和知识库配置 (progress: 0-5)
        await track_progress(job_id, user_id, "init", 0, "开始处理文档")

        # 获取单一数据库会话
        db = await get_db_session()

        # 获取文档
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            await db.close()
            await notify_task_failed(job_id, user_id, "Document not found")
            return {"status": "failed", "error": "Document not found"}

        # 获取知识库配置
        kb_config = None
        if document.knowledge_base_id:
            kb_result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == document.knowledge_base_id)
            )
            kb_config = kb_result.scalar_one_or_none()

        # 更新状态为解析中
        document.status = DocumentStatus.PARSING
        document.processing_progress = 5
        document.processing_message = "准备解析文档"
        document.processing_job_id = job_id
        await db.commit()

        file_path = document.file_path

        # Step 2: 从 MinIO 下载文件到临时目录 (progress: 5-10)
        await track_progress(job_id, user_id, "downloading", 5, "从MinIO下载文件")

        from app.services.file_service import get_file_service
        import tempfile
        import os

        file_service = get_file_service()

        try:
            # 下载文件内容
            file_content = await file_service.get_file(file_path)

            # 创建临时文件
            file_ext = Path(file_path).suffix
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
            temp_file.write(file_content)
            temp_file.close()

            local_file_path = temp_file.name
            original_filename = Path(file_path).name

            await track_progress(job_id, user_id, "downloading", 10, f"文件下载完成 ({len(file_content)} bytes)")

        except Exception as e:
            document.status = DocumentStatus.FAILED
            document.processing_message = f"文件下载失败: {str(e)}"
            await db.commit()
            await db.close()
            await notify_task_failed(job_id, user_id, str(e))
            return {"status": "failed", "error": str(e)}

        # Step 3: 解析文档 (progress: 10-30)
        await track_progress(job_id, user_id, "parsing", 10, "开始解析文档")

        # 获取解析器（MinerU 优先用于 PDF）
        extractor = ExtractorFactory.get_extractor(local_file_path)

        if not extractor:
            document.status = DocumentStatus.FAILED
            document.processing_message = "不支持的文件类型"
            await db.commit()
            await db.close()
            os.unlink(local_file_path)  # 清理临时文件
            await notify_task_failed(job_id, user_id, "Unsupported file type")
            return {"status": "failed", "error": "Unsupported file type"}

        await track_progress(job_id, user_id, "parsing", 15, f"使用 {extractor.__class__.__name__} 解析...")

        # 执行解析（使用本地文件路径）
        blocks = await extractor.extract(local_file_path)

        # 将解析结果转换为 parsed_data 格式
        parsed_data = {
            "text": "",
            "sections": [],
            "tables": [],
            "page_number": 1,
        }

        # 合并所有文本块
        all_text = []
        for block in blocks:
            block_type = block.get('type') if isinstance(block, dict) else getattr(block, 'type', None)

            if block_type == "text":
                content = block.get('content') if isinstance(block, dict) else getattr(block, 'content', '')
                all_text.append(content if content else str(block))
            elif block_type == "table":
                content = block.get('content') if isinstance(block, dict) else getattr(block, 'content', '')
                page_num = block.get('page_number') if isinstance(block, dict) else getattr(block, 'page_number', 1)
                parsed_data["tables"].append({
                    "content": content if content else str(block),
                    "page": page_num if page_num else 1,
                })

        parsed_data["text"] = "\n\n".join(all_text)

        # DEBUG: 打印解析结果
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"=== PARSED DATA DEBUG ===")
        logger.info(f"Text length: {len(parsed_data['text'])}")
        logger.info(f"Text preview: {parsed_data['text'][:200] if parsed_data['text'] else 'EMPTY'}")
        logger.info(f"Blocks count: {len(blocks)}")
        logger.info(f"Tables count: {len(parsed_data['tables'])}")

        await track_progress(job_id, user_id, "parsing", 30, f"解析完成，提取 {len(blocks)} 个内容块")

        # Step 3: 分块处理 (progress: 40-60)
        await track_progress(job_id, user_id, "chunking", 40, "开始分块处理")

        # 使用知识库配置或文档默认配置
        chunk_strategy = kb_config.chunk_strategy if kb_config else document.chunk_strategy
        chunk_size = kb_config.chunk_size if kb_config else document.chunk_size
        chunk_overlap = kb_config.chunk_overlap if kb_config else document.chunk_overlap

        # 创建分块器（使用 KB 配置）
        splitter = MixedSplitter(
            default_strategy=chunk_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        chunks = splitter.split(parsed_data, chunk_strategy)

        # DEBUG: 打印分块结果
        logger.info(f"=== CHUNKING DEBUG ===")
        logger.info(f"Chunks generated: {len(chunks)}")
        if chunks:
            logger.info(f"First chunk preview: {chunks[0].get('content', 'NO CONTENT')[:100]}")
        else:
            logger.warning("NO CHUNKS GENERATED! parsed_data might be empty or invalid")

        await track_progress(job_id, user_id, "chunking", 50, f"已生成 {len(chunks)} 个分块")

        # 存储分块到数据库（使用同一会话）
        chunk_service = ChunkService()
        db_chunks = await chunk_service.process_document_chunks(
            db, document, parsed_data, chunk_strategy
        )

        # DEBUG: 打印数据库分块结果
        logger.info(f"=== DB CHUNKS DEBUG ===")
        logger.info(f"DB chunks created: {len(db_chunks)}")
        if db_chunks:
            logger.info(f"First db_chunk id: {db_chunks[0].id}")
            logger.info(f"First db_chunk content preview: {db_chunks[0].content[:100] if db_chunks[0].content else 'EMPTY'}")

        chunks_created = [str(chunk.id) for chunk in db_chunks]

        # 更新状态
        document.status = DocumentStatus.PARSED
        document.processing_progress = 60
        document.processing_message = f"已分块 {len(chunks)} 条"
        await db.commit()

        await track_progress(job_id, user_id, "chunking", 60, "分块存储完成")

        # Step 4: 向量化 (progress: 70-90)
        embedding_model = kb_config.embedding_model if kb_config else document.embedding_model
        enable_vectorization = document.enable_vectorization

        if enable_vectorization and len(db_chunks) > 0:
            await track_progress(job_id, user_id, "vectorizing", 70, f"开始向量化（模型: {embedding_model})")

            embedding_service = get_embedding_service()
            total = len(db_chunks)
            vectorized_count = 0
            batch_size = 50

            # 获取文本内容（从 db_chunks）
            texts = [chunk.content for chunk in db_chunks]

            # 分批嵌入
            all_embeddings = []
            for start in range(0, total, batch_size):
                batch_texts = texts[start:start + batch_size]

                embeddings = await embedding_service.embed_batch(batch_texts)
                all_embeddings.extend(embeddings)

                vectorized_count = min(start + batch_size, total)
                progress = 70 + int((vectorized_count / total) * 20)  # 70-90%

                await track_progress(
                    job_id, user_id, "vectorizing", progress,
                    f"已向量化 {vectorized_count}/{total} 条"
                )

            # 存储向量到数据库 - 使用批量更新
            await track_progress(job_id, user_id, "storing_vectors", 90, "开始存储向量")

            # 构建批量更新数据（使用 db_chunks 的 ID）
            update_data = []
            for db_chunk, embedding in zip(db_chunks, all_embeddings):
                update_data.append({
                    "chunk_id": str(db_chunk.id),  # 使用真实的数据库 ID
                    "document_id": document_id,
                    "embedding": json.dumps(embedding),
                    "embedding_model": embedding_model,
                })

            # 批量更新向量（使用 chunk_id）
            if update_data:
                bulk_query = text("""
                    UPDATE document_chunks
                    SET embedding_vector = CAST(:embedding AS vector),
                        embedding_model = :embedding_model,
                        embedding_created_at = NOW()
                    WHERE id = :chunk_id
                """)
                # SQLAlchemy 2.0: execute with list of params uses executemany
                await db.execute(bulk_query, update_data)

            await db.commit()

            await track_progress(job_id, user_id, "storing_vectors", 95, "向量存储完成")

        # Step 5: 更新最终状态和统计 (progress: 100)
        # 更新文档状态
        document.status = DocumentStatus.INDEXED
        document.processing_progress = 100
        document.processing_message = "处理完成"
        document.processed_at = datetime.utcnow()
        document.vectorized_count = len(chunks) if enable_vectorization else 0

        # 更新知识库统计
        if kb_config:
            # 重新获取知识库以更新统计
            kb_result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == kb_config.id)
            )
            kb = kb_result.scalar_one_or_none()

            if kb:
                # 更新知识库的 chunk_count 和 vectorized_count
                kb.chunk_count = kb.chunk_count + len(chunks)
                if enable_vectorization:
                    kb.vectorized_count = kb.vectorized_count + len(chunks)

        await db.commit()

        # 完成
        result = {
            "status": "completed",
            "document_id": document_id,
            "chunk_count": len(chunks),
            "vectorized": enable_vectorization,
            "vectorized_count": len(chunks) if enable_vectorization else 0,
        }

        await track_progress(job_id, user_id, "complete", 100, "文档处理完成")
        await notify_task_complete(job_id, user_id, result)

        # 清理临时文件
        if local_file_path and os.path.exists(local_file_path):
            os.unlink(local_file_path)

        await db.close()
        return result

    except Exception as e:
        # 回滚事务
        if db:
            await db.rollback()

        # 清理临时文件
        if 'local_file_path' in locals() and local_file_path and os.path.exists(local_file_path):
            try:
                os.unlink(local_file_path)
            except Exception:
                pass  # 忽略清理错误

        # 清理已创建的分块
        if chunks_created and db:
            try:
                await db.execute(
                    delete(DocumentChunk).where(DocumentChunk.id.in_(chunks_created))
                )
                await db.commit()
            except Exception:
                pass  # 忽略清理错误

        # 更新文档状态为失败
        if db:
            try:
                result = await db.execute(
                    select(Document).where(Document.id == document_id)
                )
                document = result.scalar_one_or_none()

                if document:
                    document.status = DocumentStatus.FAILED
                    document.processing_message = str(e)
                    await db.commit()
            except Exception:
                pass  # 忽略更新错误

            await db.close()

        await notify_task_failed(job_id, user_id, str(e))
        return {"status": "failed", "error": str(e)}