import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import httpx

from app.services.multimodal.mineru_client import MinerUClient


class TestMinerUClient:
    """MinerU 客户端测试"""

    def test_client_init(self):
        """测试客户端初始化"""
        client = MinerUClient(base_url="http://localhost:8000")

        assert client.base_url == "http://localhost:8000"
        assert client.timeout == 300.0

    def test_client_default_url(self):
        """测试默认 URL"""
        client = MinerUClient()

        assert client.base_url == "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """测试健康检查成功"""
        with patch.object(httpx.AsyncClient, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_get.return_value = mock_response

            client = MinerUClient()
            result = await client.health_check()

            assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_parse_pdf_mock(self):
        """测试 PDF 解析（mock）"""
        with patch.object(httpx.AsyncClient, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "markdown": "# Test\nContent",
                "tables": [],
                "formulas": [],
            }
            mock_post.return_value = mock_response

            client = MinerUClient()

            # 使用临时文件测试
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(b"%PDF-1.4 test content")
                temp_path = f.name

            result = await client.parse_pdf(temp_path)

            assert "markdown" in result
            assert "# Test" in result["markdown"]

    def test_build_parse_request(self):
        """测试构建解析请求"""
        client = MinerUClient()

        data = client._build_parse_request(
            output_format="markdown",
            extract_tables=True,
            extract_formulas=True,
        )

        assert data["output_format"] == "markdown"
        assert data["extract_tables"] is True