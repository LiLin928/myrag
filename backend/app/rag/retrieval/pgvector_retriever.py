"""PGVector 检索器

执行向量相似度检索：
- 向量嵌入查询文本
- PGVector cosine similarity 搜索
- 返回相关文档片段
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.rag.embedding.embedding_service import get_embedding_service
from app.db import get_db


class PGVectorRetriever:
    """PGVector 检索器

    支持功能：
    - 向量相似度检索
    - 元数据过滤（供应商、条款类型等）
    - 项目/文档级别隔离
    """

    def __init__(
        self,
        knowledge_base_id: Optional[str] = None,  # 知识库 ID（推荐）
        project_id: Optional[int] = None,         # 项目 ID（向后兼容）
        top_k: int = 5,
        score_threshold: float = 0.0,
        dimension: int = 1536,
    ):
        """初始化检索器

        Args:
            knowledge_base_id: 知识库 ID（推荐使用）
            project_id: 项目 ID（向后兼容，已弃用）
            top_k: 返回结果数量
            score_threshold: 相似度阈值
            dimension: 向量维度
        """
        # 统一参数：优先使用 knowledge_base_id
        if knowledge_base_id and not project_id:
            try:
                project_id = int(knowledge_base_id)
            except ValueError:
                # 如果 knowledge_base_id 是 UUID 格式，保持为 None
                project_id = None

        self.project_id = project_id
        self.knowledge_base_id = knowledge_base_id
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.dimension = dimension

    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """执行向量检索（支持元数据过滤）

        Args:
            query: 查询文本
            top_k: 返回结果数量（可选，覆盖默认值）
            score_threshold: 相似度阈值（可选）
            filters: 元数据过滤条件，支持：
                - supplier: 供应商名称（metadata->>'supplier'）
                - clause_type: 条款类型（如 price_table, technical_clause）
                - document_type: 文档类型（如 投标文件, 招标文件）
                - section: 章节归属（如 商务部分, 技术部分）

        Returns:
            检索结果列表，每个结果包含：
            - id: 分块 ID
            - content: 文本内容
            - score: 相似度分数
            - document_id: 文档 ID
            - metadata: 元数据
        """
        top_k = top_k or self.top_k
        score_threshold = score_threshold or self.score_threshold

        # 嵌入查询文本
        embedding_service = get_embedding_service()
        query_embedding = await embedding_service.embed_text(query)

        # 构建查询
        async for db in get_db():
            results = await self._execute_search(
                db=db,
                embedding=query_embedding,
                top_k=top_k,
                score_threshold=score_threshold,
                filters=filters,
            )
            return results

        return []

    async def _execute_search(
        self,
        db: AsyncSession,
        embedding: List[float],
        top_k: int,
        score_threshold: float,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """执行数据库查询（支持元数据过滤）

        Args:
            db: 数据库会话
            embedding: 查询向量
            top_k: 返回数量
            score_threshold: 阈值
            filters: 元数据过滤条件

        Returns:
            检索结果
        """
        # 向量字符串
        embedding_str = json.dumps(embedding)

        # 构建过滤条件 SQL
        filter_clauses = []
        params = {
            "embedding": embedding_str,
            "top_k": top_k,
        }

        if self.project_id:
            filter_clauses.append("dc.project_id = :project_id")
            params["project_id"] = self.project_id

        # 元数据过滤
        if filters:
            if filters.get("supplier"):
                filter_clauses.append("dc.chunk_metadata->>'supplier' = :supplier")
                params["supplier"] = filters["supplier"]

            if filters.get("clause_type"):
                filter_clauses.append("dc.clause_type = :clause_type")
                params["clause_type"] = filters["clause_type"]

            if filters.get("document_type"):
                filter_clauses.append("dc.chunk_metadata->>'document_type' = :document_type")
                params["document_type"] = filters["document_type"]

            if filters.get("section"):
                filter_clauses.append("dc.chunk_metadata->>'section' = :section")
                params["section"] = filters["section"]

        # 构建完整 WHERE 子句
        where_clause = " AND ".join(filter_clauses) if filter_clauses else "TRUE"

        # 构建查询 SQL
        query_sql = text(f"""
            SELECT
                dc.id,
                dc.content,
                dc.clause_id,
                dc.clause_type,
                dc.clause_title,
                dc.page_number,
                dc.document_id,
                dc.chunk_metadata,
                1 - (dc.embedding_vector <=> :embedding::vector) as score
            FROM document_chunks dc
            WHERE dc.embedding_vector IS NOT NULL
                AND {where_clause}
            ORDER BY dc.embedding_vector <=> :embedding::vector
            LIMIT :top_k
        """)

        # 执行查询
        result = await db.execute(query_sql, params)
        rows = result.fetchall()

        # 过滤低于阈值的结果
        filtered_results = []
        for row in rows:
            score = row[-1]  # score 在最后
            if score >= score_threshold:
                filtered_results.append({
                    "id": row[0],
                    "content": row[1],
                    "clause_id": row[2],
                    "clause_type": row[3],
                    "clause_title": row[4],
                    "page_number": row[5],
                    "document_id": row[6],
                    "metadata": row[7] or {},
                    "score": score,
                })

        return filtered_results

    async def search_by_document(
        self,
        document_id: int,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """在指定文档内检索（支持元数据过滤）

        Args:
            document_id: 文档 ID
            query: 查询文本
            top_k: 返回数量
            filters: 元数据过滤条件

        Returns:
            检索结果
        """
        embedding_service = get_embedding_service()
        query_embedding = await embedding_service.embed_text(query)
        embedding_str = json.dumps(query_embedding)

        # 构建过滤条件
        filter_clauses = ["dc.document_id = :document_id"]
        params = {
            "embedding": embedding_str,
            "document_id": document_id,
            "top_k": top_k,
        }

        if filters:
            if filters.get("clause_type"):
                filter_clauses.append("dc.clause_type = :clause_type")
                params["clause_type"] = filters["clause_type"]

        where_clause = " AND ".join(filter_clauses)

        async for db in get_db():
            query_sql = text(f"""
                SELECT
                    dc.id,
                    dc.content,
                    dc.clause_id,
                    dc.clause_type,
                    dc.clause_title,
                    dc.page_number,
                    dc.chunk_metadata,
                    1 - (dc.embedding_vector <=> :embedding::vector) as score
                FROM document_chunks dc
                WHERE dc.embedding_vector IS NOT NULL
                    AND {where_clause}
                ORDER BY dc.embedding_vector <=> :embedding::vector
                LIMIT :top_k
            """)

            result = await db.execute(query_sql, params)
            rows = result.fetchall()

            return [
                {
                    "id": row[0],
                    "content": row[1],
                    "clause_id": row[2],
                    "clause_type": row[3],
                    "clause_title": row[4],
                    "page_number": row[5],
                    "metadata": row[6] or {},
                    "score": row[7],
                }
                for row in rows
            ]

        return []