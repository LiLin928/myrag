"""HTTP 请求节点

发送 HTTP 请求获取外部数据
"""

from typing import Dict, Any
import httpx
import logging

from app.workflow.nodes.base_node import BaseNode, NodeResult
from app.workflow.langfuse_tracker import create_span, end_span
from app.config import get_settings

logger = logging.getLogger(__name__)


class HTTPNode(BaseNode):
    """HTTP 请求节点"""

    node_type = "http"

    async def execute(self, state: Dict[str, Any]) -> NodeResult:
        """执行 HTTP 请求

        Args:
            state: 工作流状态

        Returns:
            NodeResult
        """
        settings = get_settings()

        # 获取配置
        url_template = self.config.get("url", "")
        method = self.config.get("method", "GET")
        headers_template = self.config.get("headers", {})
        body_template = self.config.get("body", None)
        # 支持 timeout 和 timeout_seconds 两种配置名称
        timeout = self.config.get("timeout") or self.config.get("timeout_seconds", 30)
        output_key = self.config.get("output_key", "http_response")

        # 渲染 URL（替换变量）
        url = self.render_template(url_template, state)

        # 渲染 headers（替换变量）
        headers = self._render_headers(headers_template, state)

        # 渲染 body（替换变量）
        body = self._render_body(body_template, state) if body_template else None

        # 创建 Span（如果启用）
        span = None
        if settings.langfuse_available:
            span = create_span(
                trace_id=state.get("execution_id"),
                node_type=self.node_type,
                node_name=self.node_id,
                input_data={"url": url, "method": method},
                metadata={"timeout": timeout},
            )

        # 发送请求
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    json=body if method.upper() in ["POST", "PUT", "PATCH"] and body else None,
                )

                # 解析响应
                content_type = response.headers.get("content-type", "")
                if content_type.startswith("application/json"):
                    response_body = response.json()
                else:
                    response_body = response.text

                # 构建原始输出（包含状态码等元数据）
                raw_output = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "url": str(response.url),
                    "method": method.upper(),
                }

                # 构建基础输出
                output = {output_key: response_body, "_raw": raw_output}

                # 如果配置了 output_variables，使用 map_output_variables 进行映射
                output_variables = self.config.get("output_variables")
                if output_variables and isinstance(output_variables, dict):
                    # 映射输出变量
                    output = self.map_output_variables(output, output_variables)
                    # 确保保留 _raw 元数据
                    if "_raw" not in output:
                        output["_raw"] = raw_output

                # 结束 Span
                if span:
                    end_span(span, output_data={"status_code": response.status_code})

                return NodeResult(
                    success=response.status_code < 400,
                    output=output,
                )

        except httpx.TimeoutException:
            logger.error(f"HTTP request timeout: {url}")
            if span:
                end_span(span, output_data={}, metadata={"error": f"timeout after {timeout}s"})
            return NodeResult(
                success=False,
                output={},
                error=f"Request timeout after {timeout} seconds",
            )
        except httpx.RequestError as e:
            logger.error(f"HTTP request error: {e}")
            if span:
                end_span(span, output_data={}, metadata={"error": str(e)})
            return NodeResult(
                success=False,
                output={},
                error=f"Request error: {str(e)}",
            )
        except Exception as e:
            logger.error(f"HTTP node execution error: {e}")
            if span:
                end_span(span, output_data={}, metadata={"error": str(e)})
            return NodeResult(
                success=False,
                output={},
                error=str(e),
            )

    def _render_headers(self, headers_template: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, str]:
        """渲染 headers 模板

        Args:
            headers_template: headers 配置
            state: 工作流状态

        Returns:
            渲染后的 headers 字典
        """
        rendered_headers = {}
        for key, value in headers_template.items():
            # 如果值是字符串，进行模板渲染
            if isinstance(value, str):
                rendered_headers[key] = self.render_template(value, state)
            else:
                rendered_headers[key] = str(value)
        return rendered_headers

    def _render_body(self, body_template: Any, state: Dict[str, Any]) -> Any:
        """渲染 body 模板

        Args:
            body_template: body 配置
            state: 工作流状态

        Returns:
            渲染后的 body
        """
        if isinstance(body_template, str):
            # 字符串类型，进行模板渲染
            rendered = self.render_template(body_template, state)
            # 尝试解析为 JSON
            try:
                import json
                return json.loads(rendered)
            except json.JSONDecodeError:
                return rendered
        elif isinstance(body_template, dict):
            # 字典类型，递归渲染所有值
            return self._render_dict_values(body_template, state)
        elif isinstance(body_template, list):
            # 列表类型，递归渲染所有元素
            return [self._render_body(item, state) for item in body_template]
        else:
            return body_template

    def _render_dict_values(self, data: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """递归渲染字典中的所有值

        Args:
            data: 数据字典
            state: 工作流状态

        Returns:
            渲染后的字典
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.render_template(value, state)
            elif isinstance(value, dict):
                result[key] = self._render_dict_values(value, state)
            elif isinstance(value, list):
                result[key] = [self._render_body(item, state) for item in value]
            else:
                result[key] = value
        return result