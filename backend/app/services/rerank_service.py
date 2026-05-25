"""Rerank 服务

对检索结果进行重排序，提高相关性：
- 支持 BGE Reranker 模型
- 支持 Cohere Rerank API
- 批量重排序
"""

from typing import List, Dict, Any, Optional
import logging
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)


class RerankService:
    """Rerank 重排序服务"""

    def __init__(self):
        self.settings = get_settings()
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._http_client is None:
            limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
            self._http_client = httpx.AsyncClient(timeout=60.0, limits=limits)
        return self._http_client

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        model: str = "bge-reranker-v2-m3",
        top_n: int = 10,
        provider: str = "bge",
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """重排序检索结果

        Args:
            query: 查询文本
            results: 检索结果列表，每个结果需包含 'content' 或 'text' 字段
            model: Rerank 模型名称
            top_n: 返回数量
            provider: 提供商 ('bge' 或 'cohere')
            api_base: API 基础地址（可选，使用默认配置）
            api_key: API Key（可选，使用默认配置）

        Returns:
            重排序后的结果列表（带 rerank_score）
        """
        if not results:
            return []

        # 限制 top_n 不超过结果数量
        top_n = min(top_n, len(results))

        try:
            if provider.lower() == "cohere":
                return await self._rerank_cohere(
                    query, results, model, top_n, api_base, api_key
                )
            else:
                return await self._rerank_bge(
                    query, results, model, top_n, api_base, api_key
                )
        except Exception as e:
            logger.error(f"Rerank failed: {e}")
            # 失败时返回原始结果，设置默认分数
            return self._fallback_results(results, top_n)

    async def _rerank_bge(
        self,
        query: str,
        results: List[Dict[str, Any]],
        model: str,
        top_n: int,
        api_base: Optional[str],
        api_key: Optional[str],
    ) -> List[Dict[str, Any]]:
        """BGE Reranker 重排序

        支持:
        - BGE Reranker v2 M3 (默认)
        - BGE Reranker v2 GEMMA
        - 通过 Xinference / TEI 等 API 部署的 BGE 模型

        Args:
            query: 查询文本
            results: 检索结果列表
            model: 模型名称
            top_n: 返回数量
            api_base: API 基础地址
            api_key: API Key

        Returns:
            重排序后的结果列表
        """
        client = await self._get_client()

        # 提取文档内容
        documents = []
        for r in results:
            content = r.get("content") or r.get("text") or r.get("chunk_content", "")
            documents.append(content)

        # 使用默认配置或传入的配置
        base_url = api_base or self.settings.OPENAI_API_BASE
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # 构建请求 - 兼容 TEI 和 Xinference API 格式
        payload = {
            "model": model,
            "query": query,
            "texts": documents,
            "top_n": top_n,
            "return_text": False,  # 不返回文本，节省带宽
        }

        # 尝试 TEI 格式的 API
        tei_url = f"{base_url.rstrip('/')}/rerank"

        try:
            response = await client.post(tei_url, json=payload, headers=headers)
            if response.status_code == 200:
                return self._parse_bge_response(results, response.json(), top_n)
        except Exception as e:
            logger.warning(f"TEI format rerank failed, trying Xinference format: {e}")

        # 尝试 Xinference 格式
        xinference_url = f"{base_url.rstrip('/')}/v1/rerank"
        xinference_payload = {
            "model": model,
            "query": query,
            "documents": documents,
            "top_n": top_n,
        }

        try:
            response = await client.post(
                xinference_url, json=xinference_payload, headers=headers
            )
            if response.status_code == 200:
                return self._parse_bge_response(results, response.json(), top_n)
        except Exception as e:
            logger.error(f"Xinference format rerank also failed: {e}")
            raise

        raise RuntimeError("BGE rerank request failed")

    async def _rerank_cohere(
        self,
        query: str,
        results: List[Dict[str, Any]],
        model: str,
        top_n: int,
        api_base: Optional[str],
        api_key: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Cohere Rerank API 重排序

        Args:
            query: 查询文本
            results: 检索结果列表
            model: Cohere 模型名称 (如 'rerank-english-v3.0', 'rerank-multilingual-v3.0')
            top_n: 返回数量
            api_base: API 基础地址
            api_key: Cohere API Key

        Returns:
            重排序后的结果列表
        """
        client = await self._get_client()

        # 提取文档内容
        documents = []
        for r in results:
            content = r.get("content") or r.get("text") or r.get("chunk_content", "")
            documents.append(content)

        # 使用默认配置或传入的配置
        base_url = api_base or "https://api.cohere.ai/v1"
        api_key = api_key or getattr(self.settings, "COHERE_API_KEY", "")

        if not api_key:
            raise ValueError("Cohere API key is required for reranking")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        # Cohere API 格式
        payload = {
            "model": model or "rerank-multilingual-v3.0",
            "query": query,
            "documents": documents,
            "top_n": top_n,
        }

        url = f"{base_url.rstrip('/')}/rerank"

        response = await client.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            raise RuntimeError(
                f"Cohere rerank API failed: {response.status_code} - {response.text}"
            )

        return self._parse_cohere_response(results, response.json(), top_n)

    def _parse_bge_response(
        self,
        results: List[Dict[str, Any]],
        response: Dict[str, Any],
        top_n: int,
    ) -> List[Dict[str, Any]]:
        """解析 BGE/TEI 格式的响应

        Args:
            results: 原始结果列表
            response: API 响应
            top_n: 返回数量

        Returns:
            重排序后的结果列表
        """
        reranked = []

        # TEI 格式: {"results": [{"index": 0, "relevance_score": 0.9}, ...]}
        # Xinference 格式: {"results": [{"index": 0, "relevance_score": 0.9}, ...]}
        response_results = response.get("results", [])

        for item in response_results[:top_n]:
            index = item.get("index", 0)
            score = item.get("relevance_score", 0.0)

            if 0 <= index < len(results):
                result = results[index].copy()
                result["rerank_score"] = float(score)
                result["rerank_model"] = "bge"
                reranked.append(result)

        return reranked

    def _parse_cohere_response(
        self,
        results: List[Dict[str, Any]],
        response: Dict[str, Any],
        top_n: int,
    ) -> List[Dict[str, Any]]:
        """解析 Cohere 格式的响应

        Args:
            results: 原始结果列表
            response: API 响应
            top_n: 返回数量

        Returns:
            重排序后的结果列表
        """
        reranked = []

        # Cohere 格式: {"results": [{"index": 0, "relevance_score": 0.9}, ...]}
        response_results = response.get("results", [])

        for item in response_results[:top_n]:
            index = item.get("index", 0)
            score = item.get("relevance_score", 0.0)

            if 0 <= index < len(results):
                result = results[index].copy()
                result["rerank_score"] = float(score)
                result["rerank_model"] = "cohere"
                reranked.append(result)

        return reranked

    def _fallback_results(
        self,
        results: List[Dict[str, Any]],
        top_n: int,
    ) -> List[Dict[str, Any]]:
        """失败时返回带默认分数的结果

        Args:
            results: 原始结果列表
            top_n: 返回数量

        Returns:
            带默认分数的结果列表
        """
        reranked = []
        for i, result in enumerate(results[:top_n]):
            r = result.copy()
            # 使用原始分数（如果有），否则设置默认分数
            r["rerank_score"] = result.get("score", 1.0 - i * 0.1)
            r["rerank_model"] = "fallback"
            reranked.append(r)
        return reranked

    async def rerank_batch(
        self,
        queries: List[str],
        results_list: List[List[Dict[str, Any]]],
        model: str = "bge-reranker-v2-m3",
        top_n: int = 10,
        provider: str = "bge",
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> List[List[Dict[str, Any]]]:
        """批量重排序

        Args:
            queries: 查询文本列表
            results_list: 检索结果列表的列表
            model: Rerank 模型名称
            top_n: 返回数量
            provider: 提供商 ('bge' 或 'cohere')
            api_base: API 基础地址
            api_key: API Key

        Returns:
            重排序后的结果列表的列表
        """
        if len(queries) != len(results_list):
            raise ValueError("queries and results_list must have the same length")

        reranked_list = []
        for query, results in zip(queries, results_list):
            reranked = await self.rerank(
                query=query,
                results=results,
                model=model,
                top_n=top_n,
                provider=provider,
                api_base=api_base,
                api_key=api_key,
            )
            reranked_list.append(reranked)

        return reranked_list


def get_rerank_service() -> RerankService:
    """获取 Rerank 服务实例（每次调用创建新实例）"""
    return RerankService()