"""add workflow templates table

Revision ID: 009
Revises: 008
Create Date: 2026-05-17

"""
from alembic import op
import sqlalchemy as sa

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'workflow_templates',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('definition', sa.JSON(), nullable=False),
        sa.Column('default_input_variables', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('is_builtin', sa.Boolean(), server_default='0'),
        sa.Column('usage_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )

    op.create_index('ix_workflow_templates_category', 'workflow_templates', ['category'])


def downgrade() -> None:
    op.drop_index('ix_workflow_templates_category', 'workflow_templates')
    op.drop_table('workflow_templates')