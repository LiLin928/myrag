"""HTTP 请求工具

发送 HTTP 请求获取外部数据
"""

from typing import Dict, Any, Optional
from langchain_core.tools import tool
import httpx


@tool
async def http_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Any] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """发送 HTTP 请求

    Args:
        url: 目标 URL
        method: HTTP 方法 (GET/POST/PUT/DELETE)，默认 GET
        headers: 请求头字典（可选）
        body: 请求体（可选，POST/PUT 使用）
        timeout: 超时时间（秒），默认 30

    Returns:
        响应字典，包含：
        - status: HTTP 状态码
        - body: 响应体（JSON 或文本）
        - headers: 响应头
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method.upper(),
                url=url,
                headers=headers or {},
                json=body if method.upper() in ["POST", "PUT"] else None,
            )

            # 解析响应体
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                response_body = response.json()
            else:
                response_body = response.text

            return {
                "status": response.status_code,
                "body": response_body,
                "headers": dict(response.headers),
            }

    except httpx.TimeoutException:
        return {
            "status": 0,
            "error": "Request timeout",
            "body": None,
        }
    except Exception as e:
        return {
            "status": 0,
            "error": str(e),
            "body": None,
        }


def create_http_request_tool() -> http_request:
    """创建 HTTP 请求工具实例"""
    return http_request