"""权限检查依赖"""
from typing import List
from fastapi import Depends, HTTPException, status

from app.models.user import User
from app.api.dependencies.auth import get_current_user


async def is_admin(user) -> bool:
    """检查用户是否为管理员

    Args:
        user: 用户实例

    Returns:
        是否为管理员（superuser）
    """
    return user.is_superuser


async def get_user_bound_knowledge_base_ids(user) -> List[str]:
    """获取用户绑定的知识库 ID 列表

    Args:
        user: 用户实例

    Returns:
        知识库 ID 列表（目前返回空列表，由子类实现具体逻辑）
    """
    return []


async def get_user_bound_workflow_ids(user) -> List[str]:
    """获取用户绑定的工作流 ID 列表

    Args:
        user: 用户实例

    Returns:
        工作流 ID 列表（目前返回空列表，由子类实现具体逻辑）
    """
    return []