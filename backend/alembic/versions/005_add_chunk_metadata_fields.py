"""add chunk metadata fields

Revision ID: 005
Revises: 004_add_kb_document_fields
Create Date: 2026-05-17

"""
from alembic import op
import sqlalchemy as sa

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    # DocumentChunk 表新增字段
    op.add_column('document_chunks', sa.Column('document_type', sa.String(20), nullable=True))
    op.add_column('document_chunks', sa.Column('source_filename', sa.String(255), nullable=True))

    op.add_column('document_chunks', sa.Column('section_title', sa.String(255), nullable=True))
    op.add_column('document_chunks', sa.Column('section_level', sa.Integer, server_default='1'))
    op.add_column('document_chunks', sa.Column('position_type', sa.String(32), nullable=True))

    op.add_column('document_chunks', sa.Column('user_metadata', sa.JSON, nullable=True, server_default='{}'))
    op.add_column('document_chunks', sa.Column('content_length', sa.Integer, server_default='0'))
    op.add_column('document_chunks', sa.Column('embedding_created_at', sa.DateTime, nullable=True))


def downgrade():
    op.drop_column('document_chunks', 'embedding_created_at')
    op.drop_column('document_chunks', 'content_length')
    op.drop_column('document_chunks', 'user_metadata')
    op.drop_column('document_chunks', 'position_type')
    op.drop_column('document_chunks', 'section_level')
    op.drop_column('document_chunks', 'section_title')
    op.drop_column('document_chunks', 'source_filename')
    op.drop_column('document_chunks', 'document_type')