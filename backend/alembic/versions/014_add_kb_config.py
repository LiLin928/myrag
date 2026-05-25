"""add knowledge base config fields

Revision ID: 014
Revises: 013
Create Date: 2026-05-18

"""

from alembic import op
import sqlalchemy as sa


revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    # 获取连接和检查器
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 检查 knowledge_bases 表是否存在
    tables = inspector.get_table_names()
    if 'knowledge_bases' not in tables:
        # 如果表不存在，创建完整的 knowledge_bases 表
        op.create_table(
            'knowledge_bases',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True),

            # 基本信息
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),

            # 配置
            sa.Column('embedding_model', sa.String(64), server_default='text-embedding-3-small'),
            sa.Column('vector_dimension', sa.Integer(), server_default='1536'),

            # 分块配置
            sa.Column('chunk_strategy', sa.String(20), server_default='auto'),
            sa.Column('chunk_size', sa.Integer(), server_default='800'),
            sa.Column('chunk_overlap', sa.Integer(), server_default='100'),

            # Rerank 配置
            sa.Column('rerank_model', sa.String(64), nullable=True),
            sa.Column('rerank_enabled', sa.Boolean(), server_default='false'),
            sa.Column('rerank_top_n', sa.Integer(), server_default='10'),

            # 检索配置
            sa.Column('retrieval_method', sa.String(20), server_default='hybrid'),
            sa.Column('retrieval_top_k', sa.Integer(), server_default='10'),
            sa.Column('similarity_threshold', sa.Float(), server_default='0.5'),

            # 混合检索权重
            sa.Column('vector_weight', sa.Float(), server_default='0.7'),
            sa.Column('keyword_weight', sa.Float(), server_default='0.3'),

            # 统计
            sa.Column('document_count', sa.Integer(), server_default='0'),
            sa.Column('chunk_count', sa.Integer(), server_default='0'),
            sa.Column('vectorized_count', sa.Integer(), server_default='0'),

            # 元数据
            sa.Column('kb_metadata', sa.JSON(), nullable=True),

            # 时间戳
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        )
        op.create_index('ix_knowledge_bases_user_id', 'knowledge_bases', ['user_id'])
        op.create_index('ix_knowledge_bases_project_id', 'knowledge_bases', ['project_id'])
    else:
        # 表存在，检查并添加缺失的字段
        columns = [col['name'] for col in inspector.get_columns('knowledge_bases')]

        # 分块配置
        if 'chunk_strategy' not in columns:
            op.add_column('knowledge_bases', sa.Column('chunk_strategy', sa.String(20), server_default='auto'))
        if 'chunk_size' not in columns:
            op.add_column('knowledge_bases', sa.Column('chunk_size', sa.Integer(), server_default='800'))
        if 'chunk_overlap' not in columns:
            op.add_column('knowledge_bases', sa.Column('chunk_overlap', sa.Integer(), server_default='100'))

        # Rerank 配置
        if 'rerank_model' not in columns:
            op.add_column('knowledge_bases', sa.Column('rerank_model', sa.String(64), nullable=True))
        if 'rerank_enabled' not in columns:
            op.add_column('knowledge_bases', sa.Column('rerank_enabled', sa.Boolean(), server_default='false'))
        if 'rerank_top_n' not in columns:
            op.add_column('knowledge_bases', sa.Column('rerank_top_n', sa.Integer(), server_default='10'))

        # 检索配置
        if 'retrieval_method' not in columns:
            op.add_column('knowledge_bases', sa.Column('retrieval_method', sa.String(20), server_default='hybrid'))
        if 'retrieval_top_k' not in columns:
            op.add_column('knowledge_bases', sa.Column('retrieval_top_k', sa.Integer(), server_default='10'))
        if 'similarity_threshold' not in columns:
            op.add_column('knowledge_bases', sa.Column('similarity_threshold', sa.Float(), server_default='0.5'))

        # 混合检索权重
        if 'vector_weight' not in columns:
            op.add_column('knowledge_bases', sa.Column('vector_weight', sa.Float(), server_default='0.7'))
        if 'keyword_weight' not in columns:
            op.add_column('knowledge_bases', sa.Column('keyword_weight', sa.Float(), server_default='0.3'))


def downgrade():
    # 获取连接和检查器
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'knowledge_bases' in tables:
        columns = [col['name'] for col in inspector.get_columns('knowledge_bases')]

        # 删除新添加的字段
        if 'keyword_weight' in columns:
            op.drop_column('knowledge_bases', 'keyword_weight')
        if 'vector_weight' in columns:
            op.drop_column('knowledge_bases', 'vector_weight')
        if 'similarity_threshold' in columns:
            op.drop_column('knowledge_bases', 'similarity_threshold')
        if 'retrieval_top_k' in columns:
            op.drop_column('knowledge_bases', 'retrieval_top_k')
        if 'retrieval_method' in columns:
            op.drop_column('knowledge_bases', 'retrieval_method')
        if 'rerank_top_n' in columns:
            op.drop_column('knowledge_bases', 'rerank_top_n')
        if 'rerank_enabled' in columns:
            op.drop_column('knowledge_bases', 'rerank_enabled')
        if 'rerank_model' in columns:
            op.drop_column('knowledge_bases', 'rerank_model')
        if 'chunk_overlap' in columns:
            op.drop_column('knowledge_bases', 'chunk_overlap')
        if 'chunk_size' in columns:
            op.drop_column('knowledge_bases', 'chunk_size')
        if 'chunk_strategy' in columns:
            op.drop_column('knowledge_bases', 'chunk_strategy')