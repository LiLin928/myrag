"""数据库初始化脚本"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import get_settings

settings = get_settings()


async def create_admin_user(username: str, email: str, password: str):
    """创建管理员用户"""
    from app.services.user_service import UserService

    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(db_url, echo=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        user_service = UserService(session)

        # 检查用户是否已存在
        existing = await user_service.get_by_username(username)
        if existing:
            print(f"用户 {username} 已存在")
            return

        # 创建管理员用户
        user = await user_service.create_user(
            username=username,
            email=email,
            password=password,
            full_name="Administrator",
        )
        # 设置为超级管理员
        user.is_superuser = True
        await session.commit()

        print(f"创建管理员用户成功: {user.username}")

    await engine.dispose()


def main():
    """主函数"""
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python -m app.core.init_db admin <username> <email> <password>  # 创建管理员")
        sys.exit(1)

    command = sys.argv[1]

    if command == "admin":
        if len(sys.argv) < 5:
            print("用法: python -m app.core.init_db admin <username> <email> <password>")
            sys.exit(1)
        asyncio.run(create_admin_user(sys.argv[2], sys.argv[3], sys.argv[4]))
    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()