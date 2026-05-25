import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# 测试数据库 URL
TEST_DATABASE_URL = "postgresql+asyncpg://myrag:lilin1992@192.168.137.13:5432/myrag"

# 测试引擎
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope="function")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session():
    """测试数据库 Session，测试结束后自动 rollback"""
    async with test_session_factory() as session:
        # 开始一个嵌套事务（可以在 rollback 后继续使用 session）
        async with session.begin_nested():
            yield session
        # rollback 所有变更
        await session.rollback()
        await session.close()


@pytest.fixture
async def client():
    """HTTP 测试客户端 - 延迟加载 app 以避免导入问题"""
    from app.main import app
    from app.dependencies import get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
