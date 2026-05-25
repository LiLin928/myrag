"""add kb document fields

Revision ID: 004
Revises: 003_add_role_kb_wf_bindings
Create Date: 2026-05-17

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # Document 表新增字段
    op.add_column('documents', sa.Column('chunk_strategy', sa.String(20), server_default='auto'))
    op.add_column('documents', sa.Column('chunk_size', sa.Integer, server_default='800'))
    op.add_column('documents', sa.Column('chunk_overlap', sa.Integer, server_default='100'))
    op.add_column('documents', sa.Column('chunk_count', sa.Integer, server_default='0'))

    op.add_column('documents', sa.Column('enable_vectorization', sa.Boolean, server_default='true'))
    op.add_column('documents', sa.Column('embedding_model', sa.String(64), server_default='text-embedding-3-small'))
    op.add_column('documents', sa.Column('vector_dimension', sa.Integer, server_default='1536'))
    op.add_column('documents', sa.Column('vectorized_count', sa.Integer, server_default='0'))

    op.add_column('documents', sa.Column('processing_progress', sa.Integer, server_default='0'))
    op.add_column('documents', sa.Column('processing_message', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('documents', 'processing_message')
    op.drop_column('documents', 'processing_progress')
    op.drop_column('documents', 'vectorized_count')
    op.drop_column('documents', 'vector_dimension')
    op.drop_column('documents', 'embedding_model')
    op.drop_column('documents', 'enable_vectorization')
    op.drop_column('documents', 'chunk_count')
    op.drop_column('documents', 'chunk_overlap')
    op.drop_column('documents', 'chunk_size')
    op.drop_column('documents', 'chunk_strategy')