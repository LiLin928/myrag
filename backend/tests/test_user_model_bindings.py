"""测试 User 模型的模型配置绑定关系"""

import pytest
from sqlalchemy import inspect
from app.models.user import User
from app.models.model_config import ModelConfig
from app.models.associations import user_model_configs


class TestUserModelBindings:
    """测试用户模型绑定功能"""

    def test_user_has_model_configs_relationship(self):
        """测试 User 模型有 bound_model_configs relationship"""
        # 获取 User 模型的 mapper
        mapper = inspect(User)

        # 检查 bound_model_configs 属性是否存在
        assert hasattr(User, 'bound_model_configs'), "User 模型应该有 bound_model_configs 属性"

        # 检查是否是 relationship
        from sqlalchemy.orm import RelationshipProperty
        bound_model_configs_attr = mapper.relationships.get('bound_model_configs')
        assert bound_model_configs_attr is not None, "bound_model_configs 应该是一个 relationship"
        assert isinstance(bound_model_configs_attr, RelationshipProperty), "bound_model_configs 应该是 RelationshipProperty 类型"

    def test_user_model_configs_is_many_to_many(self):
        """测试 User 和 ModelConfig 是多对多关系"""
        mapper = inspect(User)
        bound_model_configs_attr = mapper.relationships.get('bound_model_configs')

        # 检查是否是多对多关系
        assert bound_model_configs_attr.secondary is not None, "bound_model_configs 应该是多对多关系"
        assert bound_model_configs_attr.secondary == user_model_configs, \
            "bound_model_configs 应该使用 user_model_configs 关联表"

    def test_user_model_configs_back_populates(self):
        """测试 relationship 的 back_populates 配置"""
        mapper = inspect(User)
        bound_model_configs_attr = mapper.relationships.get('bound_model_configs')

        # 检查 back_populates
        assert bound_model_configs_attr.back_populates == 'users', \
            "bound_model_configs 应该 back_populates 'users'"

    def test_model_config_has_users_relationship(self):
        """测试 ModelConfig 模型有 users relationship"""
        mapper = inspect(ModelConfig)

        # 检查 users 属性是否存在
        assert hasattr(ModelConfig, 'users'), "ModelConfig 模型应该有 users 属性"

        # 检查是否是 relationship
        users_attr = mapper.relationships.get('users')
        assert users_attr is not None, "users 应该是一个 relationship"

        # 检查 back_populates
        assert users_attr.back_populates == 'bound_model_configs', \
            "users 应该 back_populates 'bound_model_configs'"