"""add tools table

Revision ID: 011
Revises: 010
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa


revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 tools 表
    op.create_table(
        'tools',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('name', sa.String(64), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tool_type', sa.Enum('http', 'mcp', name='tooltype'), nullable=False, server_default='http'),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('input_schema', sa.JSON(), nullable=True),
        sa.Column('output_schema', sa.JSON(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('mcp_connection_id', sa.String(36), nullable=True),
        sa.Column('mcp_tool_name', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 创建索引
    op.create_index('ix_tools_owner_id', 'tools', ['owner_id'])
    op.create_index('ix_tools_name', 'tools', ['name'])


def downgrade() -> None:
    op.drop_index('ix_tools_name', 'tools')
    op.drop_index('ix_tools_owner_id', 'tools')
    op.drop_table('tools')
    op.execute("DROP TYPE IF EXISTS tooltype")