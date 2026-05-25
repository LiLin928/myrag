"""统一检索服务

整合向量检索、关键词检索、混合检索：
- 根据知识库配置自动选择检索方式
- 支持 Rerank 重排序
- 返回带文档信息的检索结果

检索方法：
- vector: 纯向量相似度检索
- keyword: PostgreSQL 全文搜索
- hybrid: 向量 + 关键词混合检索（加权融合）
"""

from typing import List, Dict, Any, Optional, Literal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import asyncio
import json
import logging

from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.rag.embedding.embedding_service import get_embedding_service, get_embedding_service_from_db
from app.services.rerank_service import get_rerank_service

logger = logging.getLogger(__name__)


class RetrievalService:
    """统一检索服务"""

    def __init__(self):
        """初始化检索服务"""
        self._rerank_service = None

    async def search(
        self,
        knowledge_base_id: str,
        query: str,
        db: AsyncSession,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        search_type: Optional[Literal["vector", "hybrid", "keyword"]] = None,
    ) -> Dict[str, Any]:
        """执行检索

        Args:
            knowledge_base_id: 知识库 ID
            query: 查询文本
            db: 数据库会话
            top_k: 返回结果数量（可选，使用知识库配置）
            filters: 元数据过滤条件
            search_type: 检索类型（可选，覆盖知识库配置）

        Returns:
            检索结果字典，包含：
            - knowledge_id: 知识库 ID
            - query: 查询文本
            - method: 检索方法
            - total: 结果总数
            - results: 检索结果列表，每个结果包含：
                - id: 分块 ID
                - content: 文本内容
                - score: 相似度分数
                - vector_score: 向量检索分数（仅向量检索）
                - keyword_score: 关键词检索分数（仅关键词检索）
                - document_id: 文档 ID
                - document_filename: 文档文件名
                - metadata: 元数据
                - search_type: 检索类型
        """
        # 1. 获取知识库配置
        kb = await self._get_kb_config(db, knowledge_base_id)
        if not kb:
            logger.error(f"Knowledge base not found: {knowledge_base_id}")
            return {
                "knowledge_id": knowledge_base_id,
                "query": query,
                "method": None,
                "total": 0,
                "results": [],
            }

        # 使用配置或传入的参数
        top_k = top_k or kb.retrieval_top_k
        threshold = kb.similarity_threshold
        # 允许 search_type 覆盖知识库配置
        actual_search_type = search_type or kb.retrieval_method

        # 2. 根据检索方法执行搜索
        results = []

        if actual_search_type == "vector":
            results = await self._vector_search(db, kb, query, top_k, threshold, filters)
        elif actual_search_type == "keyword":
            results = await self._keyword_search(db, kb, query, top_k, filters)
        elif actual_search_type == "hybrid":
            results = await self._hybrid_search(db, kb, query, top_k, threshold, filters)
        else:
            # 默认使用混合检索
            logger.warning(f"Unknown retrieval method: {actual_search_type}, using hybrid")
            results = await self._hybrid_search(db, kb, query, top_k, threshold, filters)

        # 3. 如果是混合检索且启用 Rerank，执行重排序
        if actual_search_type == "hybrid" and kb.rerank_enabled and kb.rerank_model:
            rerank_top_n = min(kb.rerank_top_n, len(results))
            if rerank_top_n > 0 and results:
                results = await self._rerank_results(query, results, kb.rerank_model, rerank_top_n)

        # 4. 补充文档信息
        enriched_results = await self._enrich_results(db, results)

        return {
            "knowledge_id": knowledge_base_id,
            "query": query,
            "method": actual_search_type,
            "total": len(enriched_results),
            "results": enriched_results,
        }

    async def _get_kb_config(
        self,
        db: AsyncSession,
        knowledge_base_id: str,
    ) -> Optional[KnowledgeBase]:
        """获取知识库配置

        Args:
            db: 数据库会话
            knowledge_base_id: 知识库 ID

        Returns:
            KnowledgeBase 对象或 None
        """
        try:
            result = await db.execute(
                text("SELECT * FROM knowledge_bases WHERE id = :id"),
                {"id": knowledge_base_id}
            )
            row = result.fetchone()
            if row:
                # 将 row 转换为 KnowledgeBase 对象属性字典
                kb_dict = {
                    "id": row[0],
                    "user_id": row[1],
                    "project_id": row[2],
                    "name": row[3],
                    "description": row[4],
                    "embedding_model": row[5],
                    "vector_dimension": row[6],
                    "chunk_strategy": row[7],
                    "chunk_size": row[8],
                    "chunk_overlap": row[9],
                    "rerank_model": row[10],
                    "rerank_enabled": row[11],
                    "rerank_top_n": row[12],
                    "retrieval_method": row[13],
                    "retrieval_top_k": row[14],
                    "similarity_threshold": row[15],
                    "vector_weight": row[16],
                    "keyword_weight": row[17],
                }
                # 创建简化的配置对象
                kb = KnowledgeBase()
                for key, value in kb_dict.items():
                    setattr(kb, key, value)
                return kb
            return None
        except Exception as e:
            logger.error(f"Failed to get KB config: {e}")
            return None

    async def _vector_search(
        self,
        db: AsyncSession,
        kb: KnowledgeBase,
        query: str,
        top_k: int,
        threshold: float,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """向量检索

        Args:
            db: 数据库会话
            kb: 知识库配置
            query: 查询文本
            top_k: 返回数量
            threshold: 相似度阈值
            filters: 元数据过滤条件

        Returns:
            向量检索结果
        """
        try:
            # 从数据库获取 embedding 服务（使用知识库配置的 embedding_model）
            embedding_model = kb.embedding_model
            embedding_service = await get_embedding_service_from_db(db, embedding_model)
            query_embedding = await embedding_service.embed_text(query)

            # 如果 embedding 失败，返回空结果
            if not query_embedding or all(v == 0 for v in query_embedding):
                logger.warning(f"Embedding failed for query: {query[:50]}")
                return []

            embedding_str = json.dumps(query_embedding)

            # 获取底层 asyncpg connection
            async_connection = await db.connection()
            raw_connection = await async_connection.get_raw_connection()
            asyncpg_conn = raw_connection.driver_connection

            # 执行向量检索
            rows = await asyncpg_conn.fetch('''
                SELECT
                    dc.id,
                    dc.content,
                    dc.document_id,
                    dc.knowledge_base_id,
                    dc.page_number,
                    dc.chunk_metadata,
                    1 - (dc.embedding_vector <=> $1::vector) as score
                FROM document_chunks dc
                WHERE dc.knowledge_base_id = $2
                    AND dc.embedding_vector IS NOT NULL
                ORDER BY dc.embedding_vector <=> $1::vector
                LIMIT $3
            ''', embedding_str, kb.id, top_k)

            # 过滤低于阈值的结果
            filtered_results = []
            for row in rows:
                score = float(row['score'])
                if score >= threshold:
                    filtered_results.append({
                        "id": row['id'],
                        "content": row['content'],
                        "document_id": row['document_id'],
                        "knowledge_base_id": row['knowledge_base_id'],
                        "page_number": row['page_number'],
                        "metadata": row['chunk_metadata'] or {},
                        "vector_score": score,
                        "score": score,  # backward compatibility
                        "search_type": "vector",
                    })

            return filtered_results

        except Exception as e:
            query_preview = query[:50] + "..." if len(query) > 50 else query
            logger.error(f"Vector search failed for kb={kb.id}, query='{query_preview}': {e}")
            return []

    async def _keyword_search(
        self,
        db: AsyncSession,
        kb: KnowledgeBase,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """关键词检索（PostgreSQL 全文搜索）

        Args:
            db: 数据库会话
            kb: 知识库配置
            query: 查询文本
            top_k: 返回数量
            filters: 元数据过滤条件

        Returns:
            关键词检索结果
        """
        try:
            # 获取底层 asyncpg connection
            async_connection = await db.connection()
            raw_connection = await async_connection.get_raw_connection()
            asyncpg_conn = raw_connection.driver_connection

            # PostgreSQL 全文搜索（使用 'simple' 配置）
            rows = await asyncpg_conn.fetch('''
                SELECT
                    dc.id,
                    dc.content,
                    dc.document_id,
                    dc.knowledge_base_id,
                    dc.page_number,
                    dc.chunk_metadata,
                    ts_rank(
                        to_tsvector('simple', dc.content),
                        plainto_tsquery('simple', $1)
                    ) as score
                FROM document_chunks dc
                WHERE to_tsvector('simple', dc.content) @@ plainto_tsquery('simple', $1)
                    AND dc.knowledge_base_id = $2
                ORDER BY score DESC
                LIMIT $3
            ''', query, kb.id, top_k)

            return [
                {
                    "id": row['id'],
                    "content": row['content'],
                    "document_id": row['document_id'],
                    "knowledge_base_id": row['knowledge_base_id'],
                    "page_number": row['page_number'],
                    "metadata": row['chunk_metadata'] or {},
                    "keyword_score": float(row['score']),
                    "score": float(row['score']),  # backward compatibility
                    "search_type": "keyword",
                }
                for row in rows
            ]

        except Exception as e:
            query_preview = query[:50] + "..." if len(query) > 50 else query
            logger.error(f"Keyword search failed for kb={kb.id}, query='{query_preview}': {e}")
            return []

    async def _hybrid_search(
        self,
        db: AsyncSession,
        kb: KnowledgeBase,
        query: str,
        top_k: int,
        threshold: float,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """混合检索（向量 + 关键词）

        Args:
            db: 数据库会话
            kb: 知识库配置
            query: 查询文本
            top_k: 返回数量
            threshold: 相似度阈值
            filters: 元数据过滤条件

        Returns:
            融合后的检索结果
        """
        # 获取更多候选结果用于融合
        candidate_top_k = top_k * 2

        # 并行执行两种检索
        vector_results, keyword_results = await asyncio.gather(
            self._vector_search(db, kb, query, candidate_top_k, threshold, filters),
            self._keyword_search(db, kb, query, candidate_top_k, filters),
        )

        # 加权融合
        fused_results = self._weighted_fusion(
            vector_results,
            keyword_results,
            kb.vector_weight,
            kb.keyword_weight,
        )

        return fused_results[:top_k]

    def _weighted_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        vector_weight: float,
        keyword_weight: float,
        k: int = 60,
    ) -> List[Dict[str, Any]]:
        """加权 RRF 融合算法

        公式：RRF(d) = vector_weight / (k + rank_vector) + keyword_weight / (k + rank_keyword)

        Args:
            vector_results: 向量检索结果
            keyword_results: 关键词检索结果
            vector_weight: 向量检索权重
            keyword_weight: 关键词检索权重
            k: RRF 常数（默认 60）

        Returns:
            融合后的结果列表
        """
        # 构建 chunk_id -> 结果映射
        chunk_scores: Dict[str, Dict[str, Any]] = {}

        # 处理向量检索结果
        for rank, result in enumerate(vector_results, 1):
            chunk_id = str(result["id"])
            rrf_score = vector_weight / (k + rank)

            if chunk_id not in chunk_scores:
                chunk_scores[chunk_id] = result.copy()
                chunk_scores[chunk_id]["vector_rank"] = rank
                chunk_scores[chunk_id]["vector_score"] = result.get("score", 0.0)
                chunk_scores[chunk_id]["rrf_score"] = rrf_score
            else:
                chunk_scores[chunk_id]["rrf_score"] += rrf_score
                chunk_scores[chunk_id]["vector_rank"] = rank
                chunk_scores[chunk_id]["vector_score"] = result.get("score", 0.0)

        # 处理关键词检索结果
        for rank, result in enumerate(keyword_results, 1):
            chunk_id = str(result["id"])
            rrf_score = keyword_weight / (k + rank)

            if chunk_id not in chunk_scores:
                chunk_scores[chunk_id] = result.copy()
                chunk_scores[chunk_id]["keyword_rank"] = rank
                chunk_scores[chunk_id]["keyword_score"] = result.get("score", 0.0)
                chunk_scores[chunk_id]["rrf_score"] = rrf_score
            else:
                chunk_scores[chunk_id]["rrf_score"] += rrf_score
                chunk_scores[chunk_id]["keyword_rank"] = rank
                chunk_scores[chunk_id]["keyword_score"] = result.get("score", 0.0)

        # 按 RRF 分数排序
        sorted_results = sorted(
            chunk_scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True
        )

        # 标记检索类型
        for result in sorted_results:
            result["search_type"] = "hybrid"
            # 使用融合分数作为最终分数
            result["score"] = result["rrf_score"]

        return sorted_results

    async def _rerank_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        rerank_model: str,
        top_n: int,
    ) -> List[Dict[str, Any]]:
        """对检索结果进行重排序

        Args:
            query: 查询文本
            results: 检索结果列表
            rerank_model: Rerank 模型名称
            top_n: 返回数量

        Returns:
            重排序后的结果列表
        """
        if not results:
            return []

        try:
            rerank_service = get_rerank_service()
            reranked = await rerank_service.rerank(
                query=query,
                results=results,
                model=rerank_model,
                top_n=top_n,
            )

            # 使用 rerank_score 作为最终分数
            for result in reranked:
                if "rerank_score" in result:
                    result["score"] = result["rerank_score"]

            return reranked

        except Exception as e:
            logger.error(f"Rerank failed: {e}")
            # 失败时返回原始结果
            return results[:top_n]

    async def _enrich_results(
        self,
        db: AsyncSession,
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """补充文档信息（文件名等）

        Args:
            db: 数据库会话
            results: 检索结果列表

        Returns:
            补充文档信息后的结果列表
        """
        if not results:
            return []

        # 收集所有 document_id
        document_ids = set()
        for result in results:
            if result.get("document_id"):
                document_ids.add(result["document_id"])

        if not document_ids:
            return results

        try:
            # 批量获取文档信息
            sql = text("""
                SELECT id, filename, file_type
                FROM documents
                WHERE id = ANY(:document_ids)
            """)

            # PostgreSQL 数组参数需要特殊处理
            params = {"document_ids": list(document_ids)}
            result = await db.execute(sql, params)
            rows = result.fetchall()

            # 构建 document_id -> filename 映射
            doc_map = {}
            for row in rows:
                doc_map[row[0]] = {
                    "filename": row[1],
                    "file_type": row[2],
                }

            # 补充文档信息
            enriched_results = []
            for result in results:
                enriched = result.copy()
                doc_id = result.get("document_id")
                if doc_id and doc_id in doc_map:
                    enriched["document_filename"] = doc_map[doc_id]["filename"]
                    enriched["document_file_type"] = doc_map[doc_id]["file_type"]
                else:
                    enriched["document_filename"] = None
                    enriched["document_file_type"] = None
                enriched_results.append(enriched)

            return enriched_results

        except Exception as e:
            logger.error(f"Failed to enrich results for {len(results)} chunks: {e}")
            return results


# 全局检索服务实例（延迟初始化）
_retrieval_service: Optional[RetrievalService] = None


def get_retrieval_service() -> RetrievalService:
    """获取检索服务实例（延迟初始化）"""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service