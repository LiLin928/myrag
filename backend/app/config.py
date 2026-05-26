from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # 数据库
    DATABASE_URL: str = "postgresql://myrag:myrag123@localhost:5432/myrag"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""  # Redis 密码

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_NAME: str = "myrag-files"

    # JWT
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # Sandbox
    SANDBOX_URL: str = "http://localhost:44772"
    SANDBOX_POOL_SIZE: int = 5
    SANDBOX_CPU_LIMIT: float = 0.5
    SANDBOX_MEMORY_LIMIT: str = "200m"
    SANDBOX_TIMEOUT: int = 30
    SANDBOX_MODE: str = "server"  # "server" 使用远程 OpenSandbox SDK, "local" 使用本地 Python
    SANDBOX_HOST: str = "192.168.137.13"  # 远程 OpenSandbox 服务器地址
    SANDBOX_PORT: int = 8090  # OpenSandbox API 端口
    SANDBOX_API_KEY: str = ""  # OpenSandbox API Key
    SANDBOX_IMAGE: str = "python:3.11-slim"  # 沙箱镜像

    # 应用
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # OpenAI / Embedding API 配置
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Cohere API 配置 (用于 Rerank)
    COHERE_API_KEY: str = ""

    # DeepSeek API 配置
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    DEEPSEEK_CHAT_MODEL: str = "deepseek-chat"
    DEEPSEEK_REASONER_MODEL: str = "deepseek-reasoner"

    # MinerU Docker 服务配置
    MINERU_API_URL: str = "http://localhost:8000"
    MINERU_TIMEOUT: int = 300  # 秒，PDF 解析耗时较长

    # DeepSeek OCR 配置（使用已有的 DEEPSEEK_API_KEY）
    DEEPSEEK_OCR_MODEL: str = "deepseek-ocr"

    # 多模态解析默认后端
    MULTIMODAL_DEFAULT_BACKEND: str = "auto"  # "mineru", "deepseek_ocr", "auto"

    # 技能文件存储路径
    SKILL_STORAGE_PATH: str = "/data/skills"

    # Langfuse 配置
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "http://localhost:3030"
    LANGFUSE_ENABLED: bool = False

    # Encryption Key (用于加密存储 API Key)
    ENCRYPTION_KEY: str = ""

    @property
    def langfuse_available(self) -> bool:
        """检查 Langfuse 是否可用"""
        return (
            self.LANGFUSE_ENABLED
            and self.LANGFUSE_PUBLIC_KEY
            and self.LANGFUSE_SECRET_KEY
        )


@lru_cache()
def get_settings() -> Settings:
    """获取配置（缓存）"""
    return Settings()
