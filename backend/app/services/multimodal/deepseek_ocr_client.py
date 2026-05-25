"""DeepSeek-OCR API 客户端

使用 DeepSeek-OCR 模型进行图片 OCR 解析。
"""

from typing import Dict, Any, Optional, List
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage
import base64
from pathlib import Path
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 支持的图片格式
SUPPORTED_IMAGE_FORMATS = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]


class DeepSeekOCRClient:
    """DeepSeek-OCR API 客户端

    用于调用 DeepSeek-OCR 模型进行图片文字识别。

    Example:
        ```python
        client = DeepSeekOCRClient(api_key="your-api-key")

        # 解析图片
        result = await client.parse_image("/path/to/image.png")
        text = result["content"]
        ```
    """

    # OCR 任务类型提示词
    OCR_PROMPTS = {
        "full_parse": """请识别这张图片中的所有文字内容，并按照原文格式输出。
如果有表格，请用 Markdown 表格格式输出。
如果有数学公式，请用 LaTeX 格式输出。
保持原有的段落结构和阅读顺序。""",

        "table_extract": """请识别这张图片中的表格内容，并用 Markdown 表格格式输出。
如果没有表格，请说明。""",

        "formula_extract": """请识别这张图片中的数学公式，并用 LaTeX 格式输出。
如果没有公式，请说明。""",

        "text_only": """请识别这张图片中的纯文字内容，按阅读顺序输出。""",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """初始化客户端

        Args:
            api_key: DeepSeek API Key，默认使用配置
            model_name: 模型名称，默认使用 deepseek-ocr
        """
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.model_name = model_name or settings.DEEPSEEK_OCR_MODEL
        self._model: Optional[ChatDeepSeek] = None

    def _get_model(self) -> ChatDeepSeek:
        """获取模型实例（懒加载）"""
        if self._model is None:
            self._model = ChatDeepSeek(
                model=self.model_name,
                api_key=self.api_key,
                base_url=settings.DEEPSEEK_API_BASE,
            )
        return self._model

    def _encode_image(self, file_path: str) -> str:
        """将图片编码为 base64

        Args:
            file_path: 图片文件路径

        Returns:
            Base64 编码字符串
        """
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _get_mime_type(self, file_path: str) -> str:
        """获取图片 MIME 类型

        Args:
            file_path: 文件路径

        Returns:
            MIME 类型字符串
        """
        ext = Path(file_path).suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
        }
        return mime_map.get(ext, "image/jpeg")

    def _build_ocr_prompt(self, task: str = "full_parse") -> str:
        """构建 OCR prompt

        Args:
            task: OCR 任务类型

        Returns:
            Prompt 字符串
        """
        return self.OCR_PROMPTS.get(task, self.OCR_PROMPTS["full_parse"])

    async def parse_image(
        self,
        file_path: str,
        task: str = "full_parse",
    ) -> Dict[str, Any]:
        """解析图片文件

        Args:
            file_path: 图片文件路径
            task: OCR 任务类型

        Returns:
            解析结果，包含：
            - content: 识别的文字内容
            - tables: 表格列表（如有）
            - formulas: 公式列表（如有）
            - metadata: 元数据

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 不支持的图片格式
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        ext = path.suffix.lower()
        if ext not in SUPPORTED_IMAGE_FORMATS:
            raise ValueError(f"Unsupported image format: {ext}")

        # 编码图片
        image_base64 = self._encode_image(file_path)
        mime_type = self._get_mime_type(file_path)

        # 构建消息
        prompt = self._build_ocr_prompt(task)
        model = self._get_model()

        message = HumanMessage(content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{image_base64}"
                }
            }
        ])

        # 调用模型
        response = await model.ainvoke([message])

        # 解析响应
        return self._parse_response(response.content, task)

    async def parse_image_bytes(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        task: str = "full_parse",
    ) -> Dict[str, Any]:
        """解析图片字节流

        Args:
            image_bytes: 图片字节
            mime_type: MIME 类型
            task: OCR 任务类型

        Returns:
            解析结果
        """
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        prompt = self._build_ocr_prompt(task)
        model = self._get_model()

        message = HumanMessage(content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{image_base64}"
                }
            }
        ])

        response = await model.ainvoke([message])
        return self._parse_response(response.content, task)

    def _parse_response(
        self,
        content: str,
        task: str,
    ) -> Dict[str, Any]:
        """解析模型响应

        Args:
            content: 模型返回内容
            task: OCR 任务类型

        Returns:
            标准化的解析结果
        """
        # 简单解析：直接返回文本内容
        # 更复杂的解析可以提取表格、公式等结构
        return {
            "content": content,
            "tables": [],  # 可扩展：解析 Markdown 表格
            "formulas": [],  # 可扩展：解析 LaTeX 公式
            "metadata": {
                "task": task,
                "backend": "deepseek_ocr",
                "model": self.model_name,
            },
        }

    @staticmethod
    def supports_format(file_path: str) -> bool:
        """检查是否支持该格式

        Args:
            file_path: 文件路径

        Returns:
            是否支持
        """
        ext = Path(file_path).suffix.lower()
        return ext in SUPPORTED_IMAGE_FORMATS