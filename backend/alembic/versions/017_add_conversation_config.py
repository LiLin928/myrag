"""add conversation config enhancement

Revision ID: 017
Revises: 016
Create Date: 2026-05-19

Adds:
- system_prompt_templates table
- conversation_config_history table
- New columns to conversations table (mode, config, workflow_id, etc.)
- Default system prompt templates

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '017'
down_revision: Union[str, None] = '016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add conversation config enhancement."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. 创建 system_prompt_templates 表
    if 'system_prompt_templates' not in tables:
        op.create_table(
            'system_prompt_templates',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('description', sa.Text()),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('category', sa.String(50)),
            sa.Column('is_public', sa.Boolean(), server_default='false'),
            sa.Column('is_default', sa.Boolean(), server_default='false'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        )
        op.create_index('idx_system_prompt_templates_user', 'system_prompt_templates', ['user_id'])
        op.create_index('idx_system_prompt_templates_category', 'system_prompt_templates', ['category'])

    # 2. 创建 conversation_config_history 表
    if 'conversation_config_history' not in tables:
        op.create_table(
            'conversation_config_history',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('conversation_id', sa.String(36), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
            sa.Column('old_config', sa.JSON()),
            sa.Column('new_config', sa.JSON()),
            sa.Column('old_system_prompt_template_id', sa.String(36)),
            sa.Column('new_system_prompt_template_id', sa.String(36)),
            sa.Column('changed_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('changed_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        )
        op.create_index('idx_config_history_conversation', 'conversation_config_history', ['conversation_id'])
        op.create_index('idx_config_history_changed_by', 'conversation_config_history', ['changed_by'])

    # 3. 扩展 conversations 表
    if 'conversations' in tables:
        columns = [col['name'] for col in inspector.get_columns('conversations')]

        if 'mode' not in columns:
            op.add_column('conversations', sa.Column('mode', sa.String(20), server_default='model'))

        if 'config' not in columns:
            op.add_column('conversations', sa.Column('config', sa.JSON()))

        if 'workflow_id' not in columns:
            op.add_column('conversations', sa.Column('workflow_id', sa.String(36), sa.ForeignKey('workflows.id')))
            op.create_index('idx_conversations_workflow', 'conversations', ['workflow_id'])

        if 'system_prompt_template_id' not in columns:
            op.add_column('conversations', sa.Column('system_prompt_template_id', sa.String(36), sa.ForeignKey('system_prompt_templates.id')))
            op.create_index('idx_conversations_template', 'conversations', ['system_prompt_template_id'])

        if 'custom_system_prompt' not in columns:
            op.add_column('conversations', sa.Column('custom_system_prompt', sa.Text()))

        if 'greeting_enabled' not in columns:
            op.add_column('conversations', sa.Column('greeting_enabled', sa.Boolean(), server_default='false'))

        if 'greeting_content' not in columns:
            op.add_column('conversations', sa.Column('greeting_content', sa.Text()))

        if 'greeting_sent' not in columns:
            op.add_column('conversations', sa.Column('greeting_sent', sa.Boolean(), server_default='false'))

    # 4. 插入默认模板 (使用 PostgreSQL 的 NOW() 函数)
    # 检查是否已存在默认模板
    result = conn.execute(
        sa.text("SELECT COUNT(*) FROM system_prompt_templates WHERE is_default = true")
    )
    count = result.scalar()

    if count == 0:
        op.execute("""
            INSERT INTO system_prompt_templates (id, user_id, name, content, category, is_public, is_default, created_at)
            VALUES
            ('default-assistant', 'system', '通用助手', '你是一个专业的AI助手，请用简洁、准确的语言回答用户的问题。', '助手', true, true, NOW()),
            ('default-translator', 'system', '翻译助手', '你是一个专业的翻译助手，请准确翻译用户提供的内容，保持原文风格和语气。', '翻译', true, false, NOW()),
            ('default-coder', 'system', '代码助手', '你是一个专业的编程助手，请帮助用户解决编程问题，提供清晰的代码示例和解释。', '代码', true, false, NOW())
        """)


def downgrade() -> None:
    """Remove conversation config enhancement."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 删除 conversations 表新增字段
    if 'conversations' in tables:
        columns = [col['name'] for col in inspector.get_columns('conversations')]

        if 'greeting_sent' in columns:
            op.drop_column('conversations', 'greeting_sent')
        if 'greeting_content' in columns:
            op.drop_column('conversations', 'greeting_content')
        if 'greeting_enabled' in columns:
            op.drop_column('conversations', 'greeting_enabled')
        if 'custom_system_prompt' in columns:
            op.drop_column('conversations', 'custom_system_prompt')
        if 'system_prompt_template_id' in columns:
            op.drop_index('idx_conversations_template', table_name='conversations')
            op.drop_column('conversations', 'system_prompt_template_id')
        if 'workflow_id' in columns:
            op.drop_index('idx_conversations_workflow', table_name='conversations')
            op.drop_column('conversations', 'workflow_id')
        if 'config' in columns:
            op.drop_column('conversations', 'config')
        if 'mode' in columns:
            op.drop_column('conversations', 'mode')

    # 删除表
    if 'conversation_config_history' in tables:
        op.drop_index('idx_config_history_changed_by', table_name='conversation_config_history')
        op.drop_index('idx_config_history_conversation', table_name='conversation_config_history')
        op.drop_table('conversation_config_history')

    if 'system_prompt_templates' in tables:
        op.drop_index('idx_system_prompt_templates_category', table_name='system_prompt_templates')
        op.drop_index('idx_system_prompt_templates_user', table_name='system_prompt_templates')
        op.drop_table('system_prompt_templates')