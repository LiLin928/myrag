"""add agent tables

Revision ID: 010
Revises: 009
Create Date: 2026-05-17

"""
from alembic import op
import sqlalchemy as sa

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 agents 主表
    op.create_table(
        'agents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('model_id', sa.String(36), sa.ForeignKey('model_configs.id'), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('use_knowledge', sa.Boolean(), server_default='0'),
        sa.Column('use_tools', sa.Boolean(), server_default='0'),
        sa.Column('use_skills', sa.Boolean(), server_default='0'),
        sa.Column('search_type', sa.String(20), server_default='hybrid'),
        sa.Column('top_k', sa.Integer(), server_default='5'),
        sa.Column('score_threshold', sa.Integer(), server_default='50'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_agents_user_id', 'agents', ['user_id'])
    op.create_index('ix_agents_model_id', 'agents', ['model_id'])

    # 创建 agent_knowledge_bindings 表
    op.create_table(
        'agent_knowledge_bindings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('knowledge_base_id', sa.String(36), sa.ForeignKey('knowledge_bases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('search_type', sa.String(20), server_default='hybrid'),
        sa.Column('top_k', sa.Integer(), server_default='5'),
        sa.Column('score_threshold', sa.Float(), server_default='0.5'),
        sa.Column('priority', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_akb_agent_id', 'agent_knowledge_bindings', ['agent_id'])
    op.create_index('ix_akb_knowledge_base_id', 'agent_knowledge_bindings', ['knowledge_base_id'])

    # 创建 agent_tool_bindings 表
    op.create_table(
        'agent_tool_bindings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tool_name', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_atb_agent_id', 'agent_tool_bindings', ['agent_id'])

    # 创建 agent_skill_bindings 表
    op.create_table(
        'agent_skill_bindings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('skill_id', sa.String(36), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_asb_agent_id', 'agent_skill_bindings', ['agent_id'])
    op.create_index('ix_asb_skill_id', 'agent_skill_bindings', ['skill_id'])

    # 创建 agent_sessions 表
    op.create_table(
        'agent_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('thread_id', sa.String(64), nullable=False, unique=True),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('messages', sa.JSON(), nullable=True),
        sa.Column('message_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_as_agent_id', 'agent_sessions', ['agent_id'])
    op.create_index('ix_as_user_id', 'agent_sessions', ['user_id'])

    # 创建 agent_publishes 表
    op.create_table(
        'agent_publishes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('publish_type', sa.String(20), nullable=False),
        sa.Column('embed_code', sa.Text(), nullable=True),
        sa.Column('link_url', sa.String(255), nullable=True),
        sa.Column('api_key', sa.String(64), nullable=True),
        sa.Column('config', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('access_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_ap_agent_id', 'agent_publishes', ['agent_id'])


def downgrade() -> None:
    op.drop_table('agent_publishes')
    op.drop_table('agent_sessions')
    op.drop_table('agent_skill_bindings')
    op.drop_table('agent_tool_bindings')
    op.drop_table('agent_knowledge_bindings')
    op.drop_table('agents')