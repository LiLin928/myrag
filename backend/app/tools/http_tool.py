"""HTTP 工具执行器

执行配置化的 HTTP 请求，支持：
- URL/Headers/Body 模板变量渲染
- 认证（API Key）
- 重试策略
- 输出映射
"""

from typing import Dict, Any
import httpx
import json
import re
import logging
import asyncio

logger = logging.getLogger(__name__)


class HttpToolExecutor:
    """HTTP 工具执行器"""

    async def execute(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行 HTTP 请求"""
        # 获取配置
        url_template = config.get("url", "")
        method = config.get("method", "GET").upper()
        headers_template = config.get("headers", {})
        body_template = config.get("body_template")
        timeout = config.get("timeout", 30)
        auth_config = config.get("auth", {})
        retry_config = config.get("retry", {})
        output_mapping = config.get("output_mapping", {})

        logger.info(f"HttpToolExecutor 配置: url_template={url_template}, method={method}, input_data={input_data}")

        # 渲染模板
        url = self._render_template(url_template, input_data)
        headers = self._render_headers(headers_template, input_data, auth_config)
        body = self._render_body(body_template, input_data) if body_template else None

        logger.info(f"HttpToolExecutor 渲染后: url={url}, headers={headers}, body={body}")

        # 重试配置
        max_retries = retry_config.get("max_retries", 0)
        backoff = retry_config.get("backoff", "constant")

        # 执行请求
        for attempt in range(max_retries + 1):
            try:
                result = await self._send_request(
                    url=url,
                    method=method,
                    headers=headers,
                    body=body,
                    timeout=timeout,
                )

                # 应用输出映射
                if output_mapping and result.get("success"):
                    result["output"] = self._apply_output_mapping(
                        result["output"], output_mapping
                    )

                return result

            except httpx.TimeoutException:
                if attempt < max_retries:
                    delay = self._get_retry_delay(attempt, backoff, retry_config)
                    await asyncio.sleep(delay)
                    continue
                return {"success": False, "error": f"Request timeout after {timeout}s"}

            except httpx.RequestError as e:
                if attempt < max_retries:
                    delay = self._get_retry_delay(attempt, backoff, retry_config)
                    await asyncio.sleep(delay)
                    continue
                return {"success": False, "error": f"Request error: {str(e)}"}

            except Exception as e:
                logger.error(f"HTTP tool error: {e}")
                return {"success": False, "error": str(e)}

        return {"success": False, "error": "Max retries exceeded"}

    async def _send_request(
        self,
        url: str,
        method: str,
        headers: Dict[str, str],
        body: Any,
        timeout: int,
    ) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        logger.info(f"_send_request: url={url}, method={method}, headers={headers}")
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=body if method in ["POST", "PUT", "PATCH"] and body else None,
            )

            logger.info(f"_send_request 响应: status={response.status_code}")

            # 解析响应
            content_type = response.headers.get("content-type", "")
            if content_type.startswith("application/json"):
                response_body = response.json()
            else:
                response_body = response.text

            return {
                "success": response.status_code < 400,
                "output": response_body,
                "metadata": {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                },
            }

    def _render_template(self, template: str, input_data: Dict[str, Any]) -> str:
        """渲染模板字符串"""
        if not template:
            return template

        def replace_var(match):
            var_path = match.group(1)
            parts = var_path.split(".")
            value = input_data
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return match.group(0)
            return str(value) if value is not None else match.group(0)

        return re.sub(r"\{\{([^}]+)\}\}", replace_var, template)

    def _render_headers(
        self,
        headers_template: Dict[str, Any],
        input_data: Dict[str, Any],
        auth_config: Dict[str, Any],
    ) -> Dict[str, str]:
        """渲染 Headers"""
        headers = {}

        for key, value in headers_template.items():
            if isinstance(value, str):
                headers[key] = self._render_template(value, input_data)
            else:
                headers[key] = str(value)

        # 添加认证 Header
        auth_type = auth_config.get("type")
        if auth_type == "api_key":
            key_value = auth_config.get("key", "")
            header_name = auth_config.get("header", "Authorization")
            prefix = auth_config.get("prefix", "Bearer ")
            headers[header_name] = prefix + key_value
        elif auth_type == "bearer":
            token = auth_config.get("token", "")
            headers["Authorization"] = f"Bearer {token}"

        return headers

    def _render_body(self, body_template: Any, input_data: Dict[str, Any]) -> Any:
        """渲染请求体"""
        if isinstance(body_template, str):
            rendered = self._render_template(body_template, input_data)
            try:
                return json.loads(rendered)
            except json.JSONDecodeError:
                return rendered
        elif isinstance(body_template, dict):
            return self._render_dict(body_template, input_data)
        elif isinstance(body_template, list):
            return [self._render_body(item, input_data) for item in body_template]
        return body_template

    def _render_dict(self, data: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """递归渲染字典"""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self._render_template(value, input_data)
            elif isinstance(value, dict):
                result[key] = self._render_dict(value, input_data)
            elif isinstance(value, list):
                result[key] = [self._render_body(item, input_data) for item in value]
            else:
                result[key] = value
        return result

    def _apply_output_mapping(
        self,
        output: Any,
        mapping: Dict[str, str],
    ) -> Dict[str, Any]:
        """应用输出映射"""
        result = {}
        for target_key, source_path in mapping.items():
            value = self._get_nested_value(output, source_path)
            result[target_key] = value
        return result

    def _get_nested_value(self, data: Any, path: str) -> Any:
        """获取嵌套值"""
        if not path:
            return data

        parts = path.split(".")
        value = data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(value):
                    value = value[idx]
                else:
                    return None
            else:
                return None
        return value

    def _get_retry_delay(
        self,
        attempt: int,
        backoff: str,
        retry_config: Dict[str, Any],
    ) -> float:
        """计算重试延迟"""
        base_delay = retry_config.get("delay", 1.0)

        if backoff == "exponential":
            return base_delay * (2 ** attempt)
        elif backoff == "linear":
            return base_delay * (attempt + 1)
        else:
            return base_delay