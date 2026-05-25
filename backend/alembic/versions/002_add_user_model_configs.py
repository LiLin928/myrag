"""Add user_model_configs table

Revision ID: 002
Revises: 001
Create Date: 2026-05-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 获取连接和检查器
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 只创建 user_model_configs 关联表
    if 'user_model_configs' not in tables:
        op.create_table(
            'user_model_configs',
            sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('model_config_id', sa.String(36), sa.ForeignKey('model_configs.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('is_default', sa.Boolean(), server_default='false'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        )


def downgrade() -> None:
    # 获取连接和检查器
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 只删除 user_model_configs 表
    if 'user_model_configs' in tables:
        op.drop_table('user_model_configs')