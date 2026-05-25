"""Add role_knowledge_bases and role_workflows tables

Revision ID: 003
Revises: 002
Create Date: 2026-05-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 获取连接和检查器
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 创建 role_knowledge_bases 关联表
    if 'role_knowledge_bases' not in tables:
        op.create_table(
            'role_knowledge_bases',
            sa.Column('role_id', sa.String(36), sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('knowledge_base_id', sa.String(36), sa.ForeignKey('knowledge_bases.id', ondelete='CASCADE'), primary_key=True),
        )

    # 创建 role_workflows 关联表
    if 'role_workflows' not in tables:
        op.create_table(
            'role_workflows',
            sa.Column('role_id', sa.String(36), sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('workflow_id', sa.String(36), sa.ForeignKey('workflows.id', ondelete='CASCADE'), primary_key=True),
        )


def downgrade() -> None:
    # 获取连接和检查器
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 删除 role_workflows 表
    if 'role_workflows' in tables:
        op.drop_table('role_workflows')

    # 删除 role_knowledge_bases 表
    if 'role_knowledge_bases' in tables:
        op.drop_table('role_knowledge_bases')