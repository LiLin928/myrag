"""link documents to knowledge bases

Revision ID: 015
Revises: 014
Create Date: 2026-05-18

"""

from alembic import op
import sqlalchemy as sa


revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    # 确保 knowledge_base_id 列存在（Document 模型已有此字段）
    # 添加索引
    op.create_index('idx_document_knowledge_base', 'documents', ['knowledge_base_id'], unique=False)


def downgrade():
    op.drop_index('idx_document_knowledge_base', 'documents')