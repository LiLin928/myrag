"""多模态解析服务模块

提供 PDF/图片文档的 OCR 解析能力：
- MinerU Docker 本地部署（暂时注释）
- DeepSeek-OCR API 云端调用
"""

# from app.services.multimodal.mineru_client import MinerUClient  # 暂时注释：MinerU 解析
from app.services.multimodal.deepseek_ocr_client import DeepSeekOCRClient
from app.services.multimodal.parser_service import (
    MultimodalParserService,
    ParserBackend,
)

__all__ = [
    # "MinerUClient",  # 暂时注释：MinerU 解析
    "DeepSeekOCRClient",
    "MultimodalParserService",
    "ParserBackend",
]