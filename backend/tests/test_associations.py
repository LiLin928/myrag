"""关联表模型测试"""

import pytest
from app.models.associations import (
    role_knowledge_bases,
    role_workflows,
    user_model_configs,
)


class TestAssociationTables:
    """关联表定义测试"""

    def test_role_knowledge_bases_table_exists(self):
        """测试角色-知识库关联表存在"""
        assert role_knowledge_bases is not None
        assert role_knowledge_bases.name == "role_knowledge_bases"

    def test_role_workflows_table_exists(self):
        """测试角色-工作流关联表存在"""
        assert role_workflows is not None
        assert role_workflows.name == "role_workflows"

    def test_user_model_configs_table_exists(self):
        """测试用户-模型配置关联表存在"""
        assert user_model_configs is not None
        assert user_model_configs.name == "user_model_configs"

    def test_role_knowledge_bases_columns(self):
        """测试角色-知识库关联表列"""
        columns = [c.name for c in role_knowledge_bases.columns]
        assert "role_id" in columns
        assert "knowledge_base_id" in columns

    def test_role_workflows_columns(self):
        """测试角色-工作流关联表列"""
        columns = [c.name for c in role_workflows.columns]
        assert "role_id" in columns
        assert "workflow_id" in columns

    def test_user_model_configs_columns(self):
        """测试用户-模型配置关联表列"""
        columns = [c.name for c in user_model_configs.columns]
        assert "user_id" in columns
        assert "model_config_id" in columns
        assert "is_default" in columns
        assert "created_at" in columns