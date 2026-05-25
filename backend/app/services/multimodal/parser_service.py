"""统一多模态解析服务

整合 MinerU Docker 和 DeepSeek-OCR API，提供统一的文档解析接口。
"""

from typing import Dict, Any, Optional, List
from enum import Enum
from pathlib import Path
import logging

from app.config import get_settings
# from app.services.multimodal.mineru_client import MinerUClient  # 暂时注释：MinerU 解析
from app.services.multimodal.deepseek_ocr_client import DeepSeekOCRClient, SUPPORTED_IMAGE_FORMATS

logger = logging.getLogger(__name__)
settings = get_settings()


class ParserBackend(Enum):
    """解析后端类型"""
    # MINERU_DOCKER = "mineru_docker"  # 暂时注释：MinerU 解析
    DEEPSEEK_OCR = "deepseek_ocr"
    AUTO = "auto"


class MultimodalParserService:
    """统一多模态解析服务

    根据文件类型和大小自动选择最优解析器。

    Example:
        ```python
        service = MultimodalParserService()

        # 自动选择后端
        result = await service.parse("/path/to/document.pdf", "pdf")

        # 指定后端
        result = await service.parse(
            "/path/to/image.png",
            "image",
            backend=ParserBackend.DEEPSEEK_OCR
        )
        ```
    """

    def __init__(
        self,
        # mineru_url: Optional[str] = None,  # 暂时注释：MinerU 解析
        deepseek_api_key: Optional[str] = None,
        default_backend: ParserBackend = ParserBackend.AUTO,
    ):
        """初始化服务

        Args:
            mineru_url: MinerU 服务地址
            deepseek_api_key: DeepSeek API Key
            default_backend: 默认后端
        """
        # self.mineru_url = mineru_url or settings.MINERU_API_URL  # 暂时注释：MinerU 解析
        self.deepseek_api_key = deepseek_api_key or settings.DEEPSEEK_API_KEY
        self.default_backend = default_backend

        # 懒加载客户端
        # self._mineru_client: Optional[MinerUClient] = None  # 暂时注释：MinerU 解析
        self._deepseek_client: Optional[DeepSeekOCRClient] = None

    # def _get_mineru_client(self) -> Optional[MinerUClient]:  # 暂时注释：MinerU 解析
    #     """获取 MinerU 客户端"""
    #     if self._mineru_client is None and self.mineru_url:
    #         try:
    #             self._mineru_client = MinerUClient(base_url=self.mineru_url)
    #         except Exception as e:
    #             logger.warning(f"MinerU client init failed: {e}")
    #     return self._mineru_client

    def _get_deepseek_client(self) -> Optional[DeepSeekOCRClient]:
        """获取 DeepSeek OCR 客户端"""
        if self._deepseek_client is None and self.deepseek_api_key:
            try:
                self._deepseek_client = DeepSeekOCRClient(api_key=self.deepseek_api_key)
            except Exception as e:
                logger.warning(f"DeepSeek OCR client init failed: {e}")
        return self._deepseek_client

    def get_available_backends(self) -> List[ParserBackend]:
        """获取可用的后端列表

        Returns:
            可用的后端列表
        """
        backends = []

        # if self._get_mineru_client():  # 暂时注释：MinerU 解析
        #     backends.append(ParserBackend.MINERU_DOCKER)

        if self._get_deepseek_client():
            backends.append(ParserBackend.DEEPSEEK_OCR)

        return backends

    def _auto_select_backend(
        self,
        file_path: str,
        file_type: str,
    ) -> ParserBackend:
        """自动选择最优解析器

        选择规则：
        1. 图片文件 -> DeepSeek OCR
        2. PDF 文件：
           - MinerU 可用 -> MinerU（支持复杂布局）
           - MinerU 不可用 -> DeepSeek OCR

        Args:
            file_path: 文件路径
            file_type: 文件类型

        Returns:
            选择的解析后端
        """
        ext = Path(file_path).suffix.lower()

        # 图片文件：使用 DeepSeek OCR
        if ext in SUPPORTED_IMAGE_FORMATS:
            if self._get_deepseek_client():
                return ParserBackend.DEEPSEEK_OCR
            logger.warning("DeepSeek OCR not available for image")
            return ParserBackend.AUTO

        # PDF 文件：暂时只使用 DeepSeek OCR（MinerU 已注释）
        if file_type == "pdf" or ext == ".pdf":
            # if self._get_mineru_client():  # 暂时注释：MinerU 解析
            #     return ParserBackend.MINERU_DOCKER
            if self._get_deepseek_client():
                return ParserBackend.DEEPSEEK_OCR
            logger.warning("No backend available for PDF")
            return ParserBackend.AUTO

        # 默认：DeepSeek OCR
        return ParserBackend.DEEPSEEK_OCR

    async def parse(
        self,
        file_path: str,
        file_type: str,
        backend: Optional[ParserBackend] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """智能解析入口

        Args:
            file_path: 文件路径
            file_type: 文件类型 ("pdf", "image")
            backend: 指定后端，None 则自动选择
            **kwargs: 传递给解析器的额外参数

        Returns:
            解析结果

        Raises:
            ValueError: 无可用后端
            FileNotFoundError: 文件不存在
        """
        # 选择后端
        selected_backend = backend or self.default_backend
        if selected_backend == ParserBackend.AUTO:
            selected_backend = self._auto_select_backend(file_path, file_type)

        logger.info(f"Using backend: {selected_backend.value} for {file_path}")

        # 根据后端调用相应客户端
        # if selected_backend == ParserBackend.MINERU_DOCKER:  # 暂时注释：MinerU 解析
        #     client = self._get_mineru_client()
        #     if not client:
        #         raise ValueError("MinerU backend not available")
        #
        #     raw_result = await client.parse_pdf(file_path, **kwargs)
        #     return client.parse_mineru_response(raw_result)

        if selected_backend == ParserBackend.DEEPSEEK_OCR:
            client = self._get_deepseek_client()
            if not client:
                raise ValueError("DeepSeek OCR backend not available")

            task = kwargs.get("ocr_task", "full_parse")
            return await client.parse_image(file_path, task=task)

        else:
            raise ValueError(f"Unknown backend: {selected_backend}")

    async def health_check(self) -> Dict[str, Any]:
        """健康检查

        Returns:
            各后端状态
        """
        status = {
            # "mineru": None,  # 暂时注释：MinerU 解析
            "deepseek_ocr": None,
        }

        # 检查 MinerU  # 暂时注释：MinerU 解析
        # mineru = self._get_mineru_client()
        # if mineru:
        #     try:
        #         result = await mineru.health_check()
        #         status["mineru"] = result
        #     except Exception as e:
        #         status["mineru"] = {"status": "error", "message": str(e)}

        # 检查 DeepSeek OCR
        deepseek = self._get_deepseek_client()
        status["deepseek_ocr"] = {
            "status": "available" if deepseek else "unavailable",
            "model": self.deepseek_api_key[:8] + "..." if self.deepseek_api_key else None,
        }

        return status


# 全局服务实例
parser_service = MultimodalParserService()