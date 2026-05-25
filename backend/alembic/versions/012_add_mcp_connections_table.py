"""add mcp_connections table

Revision ID: 012
Revises: 011
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa


revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 mcp_connections 表
    op.create_table(
        'mcp_connections',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('name', sa.String(64), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('transport_type', sa.Enum('stdio', 'sse', 'websocket', name='transporttype'), nullable=False, server_default='sse'),
        sa.Column('connection_url', sa.String(512), nullable=True),
        sa.Column('command', sa.String(256), nullable=True),
        sa.Column('args', sa.JSON(), nullable=True),
        sa.Column('env_vars', sa.JSON(), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('sync_status', sa.Enum('pending', 'success', 'failed', name='syncstatus'), nullable=False, server_default='pending'),
        sa.Column('sync_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 创建索引
    op.create_index('ix_mcp_connections_owner_id', 'mcp_connections', ['owner_id'])
    op.create_index('ix_mcp_connections_name', 'mcp_connections', ['name'])


def downgrade() -> None:
    op.drop_index('ix_mcp_connections_name', 'mcp_connections')
    op.drop_index('ix_mcp_connections_owner_id', 'mcp_connections')
    op.drop_table('mcp_connections')
    op.execute("DROP TYPE IF EXISTS syncstatus")
    op.execute("DROP TYPE IF EXISTS transporttype")