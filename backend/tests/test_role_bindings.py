"""Role 关联关系测试

测试 Role 模型的 relationship 定义：
- knowledge_bases: 角色-知识库多对多关系
- workflows: 角色-工作流多对多关系
"""

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import RelationshipProperty

from app.models.role import Role
from app.models.associations import role_knowledge_bases, role_workflows
# 导入相关模型以便 SQLAlchemy 能解析 relationship
from app.models.knowledge_base import KnowledgeBase
from app.workflow.models.workflow import Workflow


class TestRoleRelationships:
    """Role 模型关联关系测试"""

    def test_role_has_knowledge_bases_relationship(self):
        """测试 Role 模型有 knowledge_bases 关联关系"""
        mapper = inspect(Role)
        relationships = {rel.key: rel for rel in mapper.relationships}

        assert "knowledge_bases" in relationships, \
            "Role 模型应该有 knowledge_bases 关联关系"

    def test_role_has_workflows_relationship(self):
        """测试 Role 模型有 workflows 关联关系"""
        mapper = inspect(Role)
        relationships = {rel.key: rel for rel in mapper.relationships}

        assert "workflows" in relationships, \
            "Role 模型应该有 workflows 关联关系"

    def test_knowledge_bases_relationship_config(self):
        """测试 knowledge_bases 关联关系配置正确"""
        mapper = inspect(Role)
        relationships = {rel.key: rel for rel in mapper.relationships}

        rel = relationships.get("knowledge_bases")
        assert rel is not None, "knowledge_bases 关联关系应该存在"

        # 验证是多对多关系
        assert isinstance(rel, RelationshipProperty), \
            "knowledge_bases 应该是 Relationship 类型"

        # 验证 secondary 表是 role_knowledge_bases
        assert rel.secondary is not None, \
            "knowledge_bases 应该有 secondary 表"
        assert rel.secondary.name == "role_knowledge_bases", \
            "knowledge_bases 的 secondary 表应该是 role_knowledge_bases"

    def test_workflows_relationship_config(self):
        """测试 workflows 关联关系配置正确"""
        mapper = inspect(Role)
        relationships = {rel.key: rel for rel in mapper.relationships}

        rel = relationships.get("workflows")
        assert rel is not None, "workflows 关联关系应该存在"

        # 验证是多对多关系
        assert isinstance(rel, RelationshipProperty), \
            "workflows 应该是 Relationship 类型"

        # 验证 secondary 表是 role_workflows
        assert rel.secondary is not None, \
            "workflows 应该有 secondary 表"
        assert rel.secondary.name == "role_workflows", \
            "workflows 的 secondary 表应该是 role_workflows"


class TestRoleAssociationTables:
    """关联表与 Role 模型集成测试"""

    def test_role_knowledge_bases_table_columns(self):
        """测试 role_knowledge_bases 表有正确的列"""
        columns = {c.name: c for c in role_knowledge_bases.columns}

        assert "role_id" in columns, "应该有 role_id 列"
        assert "knowledge_base_id" in columns, "应该有 knowledge_base_id 列"

    def test_role_workflows_table_columns(self):
        """测试 role_workflows 表有正确的列"""
        columns = {c.name: c for c in role_workflows.columns}

        assert "role_id" in columns, "应该有 role_id 列"
        assert "workflow_id" in columns, "应该有 workflow_id 列"