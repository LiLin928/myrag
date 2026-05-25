"""add fulltext search support

Revision ID: 016
Revises: 015
Create Date: 2026-05-18

Adds:
- content_tsv column (tsvector) for full-text search
- knowledge_base_id column for KB-level search
- GIN index for fast tsvector queries
- Trigger to auto-update content_tsv on INSERT/UPDATE

"""

from alembic import op
import sqlalchemy as sa


revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade():
    """Add full-text search support to document_chunks table."""

    # 1. Add content_tsv column for tsvector
    op.add_column(
        'document_chunks',
        sa.Column('content_tsv', sa.Text(), nullable=True)
    )

    # 2. Add knowledge_base_id column
    op.add_column(
        'document_chunks',
        sa.Column('knowledge_base_id', sa.String(36), nullable=True)
    )

    # 2.1 Add foreign key constraint to knowledge_bases table
    op.create_foreign_key(
        'fk_document_chunks_knowledge_base',
        'document_chunks',
        'knowledge_bases',
        ['knowledge_base_id'],
        ['id']
    )

    # 3. Create index on knowledge_base_id
    op.create_index(
        'idx_document_chunks_knowledge_base_id',
        'document_chunks',
        ['knowledge_base_id'],
        unique=False
    )

    # 4. Create GIN index for fulltext search
    op.execute("""
        CREATE INDEX idx_document_chunks_content_tsv
        ON document_chunks
        USING gin(to_tsvector('simple', content))
    """)

    # 5. Create trigger function for auto-updating content_tsv
    op.execute("""
        CREATE OR REPLACE FUNCTION update_content_tsv()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.content_tsv := to_tsvector('simple', COALESCE(NEW.content, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    # 6. Create trigger
    op.execute("""
        CREATE TRIGGER trg_update_content_tsv
        BEFORE INSERT OR UPDATE ON document_chunks
        FOR EACH ROW
        EXECUTE FUNCTION update_content_tsv()
    """)

    # 7. Update existing data - set content_tsv from content
    op.execute("""
        UPDATE document_chunks
        SET content_tsv = to_tsvector('simple', COALESCE(content, ''))
    """)

    # 8. Update existing data - sync knowledge_base_id from documents table
    op.execute("""
        UPDATE document_chunks dc
        SET knowledge_base_id = d.knowledge_base_id
        FROM documents d
        WHERE dc.document_id = d.id
        AND d.knowledge_base_id IS NOT NULL
    """)


def downgrade():
    """Remove full-text search support from document_chunks table."""

    # 1. Drop trigger
    op.execute("""
        DROP TRIGGER IF EXISTS trg_update_content_tsv ON document_chunks
    """)

    # 2. Drop trigger function
    op.execute("""
        DROP FUNCTION IF EXISTS update_content_tsv()
    """)

    # 3. Drop GIN index
    op.execute("""
        DROP INDEX IF EXISTS idx_document_chunks_content_tsv
    """)

    # 4. Drop knowledge_base_id index
    op.drop_index('idx_document_chunks_knowledge_base_id', 'document_chunks')

    # 4.1 Drop foreign key constraint
    op.drop_constraint('fk_document_chunks_knowledge_base', 'document_chunks', type_='foreignkey')

    # 5. Drop columns
    op.drop_column('document_chunks', 'knowledge_base_id')
    op.drop_column('document_chunks', 'content_tsv')