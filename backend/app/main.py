from dotenv import load_dotenv

# 加载 .env 文件（显式加载，确保环境变量正确）
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.config import get_settings
from app.api.routes import api_router

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Starting MyRAG application", env=settings.APP_ENV)
    yield
    logger.info("Shutting down MyRAG application")


app = FastAPI(
    title="MyRAG API",
    description="RAG + Agent Workflow Platform",
    version="0.1.0",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "MyRAG API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }