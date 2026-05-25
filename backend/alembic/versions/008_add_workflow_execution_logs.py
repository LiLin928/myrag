"""add workflow execution logs table

Revision ID: 008
Revises: 007
Create Date: 2026-05-17

"""
from alembic import op
import sqlalchemy as sa
from app.workflow.models.workflow_execution_log import LogEventType

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'workflow_execution_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('execution_id', sa.String(36), sa.ForeignKey('workflow_executions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('node_id', sa.String(64), nullable=False),
        sa.Column('node_name', sa.String(128), nullable=True),
        sa.Column('node_type', sa.String(32), nullable=True),
        sa.Column('event_type', sa.Enum(LogEventType), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('output_data', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('progress_percent', sa.Integer(), nullable=True),
        sa.Column('progress_message', sa.Text(), nullable=True),
    )

    # 创建索引
    op.create_index('ix_execution_logs_execution_id', 'workflow_execution_logs', ['execution_id'])
    op.create_index('ix_execution_logs_node_id', 'workflow_execution_logs', ['node_id'])
    op.create_index('ix_execution_logs_event_type', 'workflow_execution_logs', ['event_type'])
    op.create_index('ix_execution_logs_timestamp', 'workflow_execution_logs', ['timestamp'])


def downgrade() -> None:
    op.drop_index('ix_execution_logs_timestamp', table_name='workflow_execution_logs')
    op.drop_index('ix_execution_logs_event_type', table_name='workflow_execution_logs')
    op.drop_index('ix_execution_logs_node_id', table_name='workflow_execution_logs')
    op.drop_index('ix_execution_logs_execution_id', table_name='workflow_execution_logs')
    op.drop_table('workflow_execution_logs')