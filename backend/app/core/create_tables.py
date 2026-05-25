"""数据库表创建脚本"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.models import Base

settings = get_settings()


async def create_tables():
    """创建所有数据库表"""
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(db_url, echo=True)

    async with engine.begin() as conn:
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("数据库表创建完成")


async def main():
    """主函数"""
    print("开始创建数据库表...")
    await create_tables()

    # 创建默认管理员用户
    from app.core.init_db import create_admin_user
    await create_admin_user("admin", "admin@example.com", "admin123")


if __name__ == "__main__":
    asyncio.run(main())