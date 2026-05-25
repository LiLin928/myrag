"""Add document enums

Revision ID: 018
Revises: 017
Create Date: 2026-05-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '018'
down_revision: Union[str, None] = '017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 documentstatus 枚举类型
    documentstatus_enum = postgresql.ENUM(
        'pending', 'parsing', 'parsed', 'vectorizing', 'indexing', 'indexed', 'completed', 'compiled', 'failed',
        name='documentstatus',
        create_type=True
    )
    documentstatus_enum.create(op.get_bind(), checkfirst=True)

    # 创建 documenttype 枚举类型
    documenttype_enum = postgresql.ENUM(
        'pdf', 'word', 'markdown', 'text', 'html', 'image',
        name='documenttype',
        create_type=True
    )
    documenttype_enum.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    # 删除枚举类型
    op.execute("DROP TYPE IF EXISTS documentstatus")
    op.execute("DROP TYPE IF EXISTS documenttype")