"""Add workflows and workflow_executions tables

Revision ID: 007
Revises: 006
Create Date: 2026-05-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.workflow.models.workflow import WorkflowStatus
from app.workflow.models.execution import ExecutionStatus

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get connection and inspector
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create workflows table if not exists
    if 'workflows' not in tables:
        op.create_table(
            'workflows',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=True),
            sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('version', sa.String(20), server_default='1.0.0'),
            sa.Column('status', sa.Enum(WorkflowStatus), server_default='draft'),
            sa.Column('definition', sa.JSON(), nullable=True),
            sa.Column('tags', sa.JSON(), nullable=True),
            sa.Column('wf_metadata', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
            sa.Column('published_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_workflows_project_id', 'workflows', ['project_id'])
        op.create_index('ix_workflows_user_id', 'workflows', ['user_id'])
        op.create_index('ix_workflows_status', 'workflows', ['status'])

    # Create workflow_executions table if not exists
    if 'workflow_executions' not in tables:
        op.create_table(
            'workflow_executions',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('workflow_id', sa.String(36), sa.ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False),
            sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('status', sa.Enum(ExecutionStatus), server_default='pending'),
            sa.Column('thread_id', sa.String(64), nullable=False, unique=True),
            sa.Column('current_node', sa.String(64), nullable=True),
            sa.Column('node_outputs', sa.JSON(), nullable=True),
            sa.Column('variables', sa.JSON(), nullable=True),
            sa.Column('human_prompt', sa.Text(), nullable=True),
            sa.Column('human_input', sa.Text(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('error_node', sa.String(64), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        )
        op.create_index('ix_workflow_executions_workflow_id', 'workflow_executions', ['workflow_id'])
        op.create_index('ix_workflow_executions_user_id', 'workflow_executions', ['user_id'])
        op.create_index('ix_workflow_executions_status', 'workflow_executions', ['status'])


def downgrade() -> None:
    # Get connection and inspector
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Drop workflow_executions table
    if 'workflow_executions' in tables:
        op.drop_index('ix_workflow_executions_status', table_name='workflow_executions')
        op.drop_index('ix_workflow_executions_user_id', table_name='workflow_executions')
        op.drop_index('ix_workflow_executions_workflow_id', table_name='workflow_executions')
        op.drop_table('workflow_executions')

    # Drop workflows table
    if 'workflows' in tables:
        op.drop_index('ix_workflows_status', table_name='workflows')
        op.drop_index('ix_workflows_user_id', table_name='workflows')
        op.drop_index('ix_workflows_project_id', table_name='workflows')
        op.drop_table('workflows')