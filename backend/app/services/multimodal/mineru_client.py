"""MinerU Docker 服务客户端

通过 HTTP API 调用本地部署的 MinerU 服务进行 PDF 解析。
"""

import httpx
from typing import Dict, Any, Optional
from pathlib import Path
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MinerUClient:
    """MinerU Docker 服务客户端

    用于调用 MinerU Docker 容器提供的 PDF 解析 API。

    Example:
        ```python
        client = MinerUClient()

        # 健康检查
        status = await client.health_check()

        # 解析 PDF
        result = await client.parse_pdf("/path/to/document.pdf")
        markdown = result["markdown"]
        ```
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        """初始化客户端

        Args:
            base_url: MinerU 服务地址，默认使用配置
            timeout: 请求超时时间（秒），默认使用配置
        """
        self.base_url = base_url or settings.MINERU_API_URL
        self.timeout = timeout or settings.MINERU_TIMEOUT
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取异步 HTTP 客户端（懒加载）"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> Dict[str, Any]:
        """健康检查

        Returns:
            服务状态信息
        """
        client = await self._get_client()

        try:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"MinerU health check failed: {e}")
            return {"status": "error", "message": str(e)}

    def _build_parse_request(
        self,
        output_format: str = "markdown",
        extract_tables: bool = True,
        extract_formulas: bool = True,
        extract_images: bool = False,
    ) -> Dict[str, Any]:
        """构建解析请求参数

        Args:
            output_format: 输出格式 ("markdown", "json")
            extract_tables: 是否提取表格
            extract_formulas: 是否提取公式
            extract_images: 是否提取图片

        Returns:
            请求参数字典
        """
        return {
            "output_format": output_format,
            "extract_tables": extract_tables,
            "extract_formulas": extract_formulas,
            "extract_images": extract_images,
        }

    async def parse_pdf(
        self,
        file_path: str,
        output_format: str = "markdown",
        extract_tables: bool = True,
        extract_formulas: bool = True,
    ) -> Dict[str, Any]:
        """解析 PDF 文件

        Args:
            file_path: PDF 文件路径
            output_format: 输出格式
            extract_tables: 是否提取表格
            extract_formulas: 是否提取公式

        Returns:
            解析结果，包含：
            - markdown: Markdown 文本
            - tables: 表格列表
            - formulas: 公式列表
            - metadata: 元数据

        Raises:
            FileNotFoundError: 文件不存在
            httpx.HTTPError: API 调用失败
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        client = await self._get_client()

        # 构建请求
        data = self._build_parse_request(
            output_format=output_format,
            extract_tables=extract_tables,
            extract_formulas=extract_formulas,
        )

        # 读取文件并上传
        with open(file_path, "rb") as f:
            files = {
                "file": (path.name, f, "application/pdf"),
            }

            try:
                response = await client.post(
                    f"{self.base_url}/parse",
                    files=files,
                    data=data,
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"MinerU parse failed: {e.response.status_code}")
                raise
            except httpx.RequestError as e:
                logger.error(f"MinerU request error: {e}")
                raise

    async def parse_pdf_bytes(
        self,
        file_bytes: bytes,
        filename: str = "document.pdf",
        output_format: str = "markdown",
    ) -> Dict[str, Any]:
        """解析 PDF 字节流

        Args:
            file_bytes: PDF 文件字节
            filename: 文件名（用于请求）
            output_format: 输出格式

        Returns:
            解析结果
        """
        client = await self._get_client()
        data = self._build_parse_request(output_format=output_format)

        files = {
            "file": (filename, file_bytes, "application/pdf"),
        }

        response = await client.post(
            f"{self.base_url}/parse",
            files=files,
            data=data,
        )
        response.raise_for_status()
        return response.json()

    def parse_mineru_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """解析 MinerU 响应格式

        将 MinerU API 响应转换为统一的格式。

        Args:
            response: MinerU API 响应

        Returns:
            标准化的解析结果
        """
        return {
            "content": response.get("markdown", ""),
            "tables": response.get("tables", []),
            "formulas": response.get("formulas", []),
            "images": response.get("images", []),
            "metadata": {
                "pages": response.get("page_count", 0),
                "parse_time": response.get("parse_time", 0),
                "backend": "mineru",
            },
        }