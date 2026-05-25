"""add skill enhancement (multi-file, version, alias)

Revision ID: 013
Revises: 012
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa


revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add new columns to skills table
    op.add_column('skills', sa.Column('internal_name', sa.String(64), nullable=True))
    op.add_column('skills', sa.Column('display_name', sa.String(128), nullable=True))
    op.add_column('skills', sa.Column('is_public', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('skills', sa.Column('entry_command', sa.String(256), nullable=True, server_default='python main.py'))
    op.add_column('skills', sa.Column('working_directory', sa.String(512), nullable=True))

    # 2. Migrate existing data: name -> internal_name and display_name
    op.execute("""
        UPDATE skills
        SET internal_name = name,
            display_name = name
    """)

    # Make internal_name not null after migration
    op.alter_column('skills', 'internal_name', nullable=False)

    # Create unique index for internal_name
    op.create_unique_constraint('uq_skills_internal_name', 'skills', ['internal_name'])
    op.create_index('ix_skills_internal_name', 'skills', ['internal_name'])
    op.create_index('ix_skills_is_public', 'skills', ['is_public'])

    # 3. Create skill_files table
    op.create_table(
        'skill_files',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('skill_id', sa.String(36), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_path', sa.String(255), nullable=False),
        sa.Column('file_type', sa.String(32), nullable=True),
        sa.Column('file_size', sa.Integer(), server_default='0'),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('is_entry', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes for skill_files
    op.create_index('ix_skill_files_skill_id', 'skill_files', ['skill_id'])
    op.create_index('ix_skill_files_skill_path', 'skill_files', ['skill_id', 'file_path'], unique=True)

    # 4. Create skill_versions table
    op.create_table(
        'skill_versions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('skill_id', sa.String(36), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('files_manifest', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
    )

    # Create indexes for skill_versions
    op.create_index('ix_skill_versions_skill_id', 'skill_versions', ['skill_id'])
    op.create_index('ix_skill_versions_created_by', 'skill_versions', ['created_by'])
    op.create_index('ix_skill_versions_skill_number', 'skill_versions', ['skill_id', 'version_number'], unique=True)

    # 5. Create legacy file records for existing skills (code -> main.py)
    op.execute("""
        INSERT INTO skill_files (id, skill_id, file_path, file_type, is_entry, created_at, updated_at)
        SELECT
            'legacy-' || id as id,
            id as skill_id,
            'main.py' as file_path,
            'python' as file_type,
            true as is_entry,
            created_at,
            updated_at
        FROM skills
        WHERE code IS NOT NULL AND code != ''
    """)

    # 6. Create initial version snapshots for existing skills
    op.execute("""
        INSERT INTO skill_versions (id, skill_id, version_number, files_manifest, created_at, created_by)
        SELECT
            'v1-' || id as id,
            id as skill_id,
            1 as version_number,
            '[{"path": "main.py", "hash": "legacy", "size": 0}]' as files_manifest,
            created_at,
            user_id as created_by
        FROM skills
    """)


def downgrade() -> None:
    # Drop skill_versions table
    op.drop_index('ix_skill_versions_skill_number', 'skill_versions')
    op.drop_index('ix_skill_versions_created_by', 'skill_versions')
    op.drop_index('ix_skill_versions_skill_id', 'skill_versions')
    op.drop_table('skill_versions')

    # Drop skill_files table
    op.drop_index('ix_skill_files_skill_path', 'skill_files')
    op.drop_index('ix_skill_files_skill_id', 'skill_files')
    op.drop_table('skill_files')

    # Remove new columns from skills table
    op.drop_index('ix_skills_is_public', 'skills')
    op.drop_index('ix_skills_internal_name', 'skills')
    op.drop_constraint('uq_skills_internal_name', 'skills', type_='unique')
    op.drop_column('skills', 'working_directory')
    op.drop_column('skills', 'entry_command')
    op.drop_column('skills', 'is_public')
    op.drop_column('skills', 'display_name')
    op.drop_column('skills', 'internal_name')