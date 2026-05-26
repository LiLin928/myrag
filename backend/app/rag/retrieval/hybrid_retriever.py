"""混合检索器

结合向量检索和关键词检索：
- 向量检索：语义相似度匹配
- 关键词检索：精确匹配（PostgreSQL全文搜索）
- 加权融合：RRF（Reciprocal Rank Fusion）算法

适用场景：
- 投标文件中同时需要语义匹配和专业术语精确匹配
- 例如：查询"供应商报价"既要匹配语义相关内容，也要精确匹配"报价单"等关键词
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.rag.embedding.embedding_service import get_embedding_service
from app.rag.retrieval.pgvector_retriever import PGVectorRetriever
from app.db import get_db


class HybridRetriever:
    """混合检索器：向量 + 关键词"""

    def __init__(
        self,
        knowledge_base_id: Optional[str] = None,  # 知识库 ID（推荐）
        project_id: Optional[int] = None,         # 项目 ID（向后兼容）
        embedding_model: Optional[str] = None,    # embedding 模型名称
        embedding_config: Optional[Any] = None,   # embedding 配置对象
        top_k: int = 5,
        score_threshold: float = 0.0,
        # 混合检索权重
        vector_weight: float = 0.7,  # 向量检索权重
        keyword_weight: float = 0.3,  # 关键词检索权重
    ):
        """初始化混合检索器

        Args:
            knowledge_base_id: 知识库 ID（推荐使用）
            project_id: 项目 ID（向后兼容，已弃用）
            embedding_model: embedding 模型名称
            embedding_config: EmbeddingModelConfig 对象（完整配置）
            top_k: 返回结果数量
            score_threshold: 相似度阈值
            vector_weight: 向量检索权重（0-1）
            keyword_weight: 关键词检索权重（0-1）
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
        self.embedding_model = embedding_model
        self.embedding_config = embedding_config
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

        # 向量检索器（传递 knowledge_base_id 和 embedding 配置）
        self.vector_retriever = PGVectorRetriever(
            knowledge_base_id=knowledge_base_id,
            project_id=project_id,
            embedding_model=embedding_model,
            embedding_config=embedding_config,
            top_k=top_k * 2,  # 获取更多候选结果用于融合
            score_threshold=0.0,
        )

    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """执行混合检索

        Args:
            query: 查询文本
            filters: 元数据过滤条件
            top_k: 返回数量

        Returns:
            融合后的检索结果
        """
        top_k = top_k or self.top_k

        # 并行执行两种检索
        vector_results = await self._vector_search(query, filters)
        keyword_results = await self._keyword_search(query, filters)

        # RRF 融合
        fused_results = self._rrf_fusion(vector_results, keyword_results)

        # 返回 top_k 结果
        return fused_results[:top_k]

    async def _vector_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """向量检索"""
        return await self.vector_retriever.search(query, filters=filters)

    async def _keyword_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """关键词检索（PostgreSQL 全文搜索）"""

        async for db in get_db():
            # 构建过滤条件
            filter_clauses = []
            params = {"query": query, "top_k": self.top_k * 2}

            # 优先使用 knowledge_base_id（UUID 格式），其次使用 project_id
            if self.knowledge_base_id:
                filter_clauses.append("dc.knowledge_base_id = :knowledge_base_id")
                params["knowledge_base_id"] = self.knowledge_base_id
            elif self.project_id:
                filter_clauses.append("dc.project_id = :project_id")
                params["project_id"] = self.project_id

            if filters:
                if filters.get("supplier"):
                    filter_clauses.append("dc.chunk_metadata->>'supplier' = :supplier")
                    params["supplier"] = filters["supplier"]
                if filters.get("clause_type"):
                    filter_clauses.append("dc.clause_type = :clause_type")
                    params["clause_type"] = filters["clause_type"]

            where_clause = " AND ".join(filter_clauses) if filter_clauses else "TRUE"

            # PostgreSQL 全文搜索 - 使用 simple 配置（不需要中文分词扩展）
            # 或者使用 ILIKE 进行简单的文本匹配
            sql = text("""
                SELECT
                    dc.id,
                    dc.content,
                    dc.clause_id,
                    dc.clause_type,
                    dc.clause_title,
                    dc.page_number,
                    dc.document_id,
                    dc.chunk_metadata,
                    CASE WHEN dc.content ILIKE '%' || :query || '%' THEN 1.0 ELSE 0.5 END as score
                FROM document_chunks dc
                WHERE dc.content ILIKE '%' || :query || '%'
                    AND {where_clause}
                ORDER BY score DESC
                LIMIT :top_k
            """.format(where_clause=where_clause))

            result = await db.execute(sql, params)
            rows = result.fetchall()

            return [
                {
                    "id": row[0],
                    "content": row[1],
                    "clause_id": row[2],
                    "clause_type": row[3],
                    "clause_title": row[4],
                    "page_number": row[5],
                    "document_id": row[6],
                    "metadata": row[7] or {},
                    "score": float(row[8]),
                    "source": "keyword",
                }
                for row in rows
            ]

        return []

    def _rrf_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        k: int = 60,
    ) -> List[Dict[str, Any]]:
        """RRF（Reciprocal Rank Fusion）融合算法

        公式：RRF(d) = Σ 1/(k + rank(d))

        Args:
            vector_results: 向量检索结果
            keyword_results: 关键词检索结果
            k: RRF 常数（默认 60）

        Returns:
            融合后的结果列表
        """
        # 构建 chunk_id -> 结果映射
        chunk_scores: Dict[str, Dict[str, Any]] = {}

        # 处理向量检索结果
        for rank, result in enumerate(vector_results, 1):
            chunk_id = str(result["id"])
            rrf_score = self.vector_weight / (k + rank)

            if chunk_id not in chunk_scores:
                chunk_scores[chunk_id] = result.copy()
                chunk_scores[chunk_id]["vector_rank"] = rank
                chunk_scores[chunk_id]["rrf_score"] = rrf_score
            else:
                chunk_scores[chunk_id]["rrf_score"] += rrf_score
                chunk_scores[chunk_id]["vector_rank"] = rank

        # 处理关键词检索结果
        for rank, result in enumerate(keyword_results, 1):
            chunk_id = str(result["id"])
            rrf_score = self.keyword_weight / (k + rank)

            if chunk_id not in chunk_scores:
                chunk_scores[chunk_id] = result.copy()
                chunk_scores[chunk_id]["keyword_rank"] = rank
                chunk_scores[chunk_id]["rrf_score"] = rrf_score
            else:
                chunk_scores[chunk_id]["rrf_score"] += rrf_score
                chunk_scores[chunk_id]["keyword_rank"] = rank

        # 按 RRF 分数排序
        sorted_results = sorted(
            chunk_scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True
        )

        # 标记来源
        for result in sorted_results:
            result["search_type"] = "hybrid"

        return sorted_results