"""PGVector 扩展设置

在 PostgreSQL 中启用 pgvector 扩展，
创建向量索引，支持向量相似度检索
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def setup_vector_extension(db: AsyncSession):
    """设置 PGVector 扩展

    Args:
        db: 数据库会话
    """
    # 创建 pgvector 扩展
    await db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    await db.commit()


async def create_vector_index(db: AsyncSession, table: str, column: str, dimension: int = 1536):
    """创建向量索引

    Args:
        db: 数据库会话
        table: 表名
        column: 向量列名
        dimension: 向量维度
    """
    # HNSW 索引（适合各种规模数据）
    index_name = f"{table}_{column}_idx"

    await db.execute(text(f"""
        CREATE INDEX IF NOT EXISTS {index_name}
        ON {table}
        USING hnsw ({column} vector_cosine_ops)
    """))
    await db.commit()


async def drop_vector_index(db: AsyncSession, table: str, column: str):
    """删除向量索引"""
    index_name = f"{table}_{column}_idx"
    await db.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
    await db.commit()