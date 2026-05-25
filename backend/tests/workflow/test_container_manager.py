# backend/tests/workflow/test_container_manager.py

import pytest
from unittest.mock import MagicMock, patch


def test_container_manager_init():
    """测试容器管理器初始化"""
    from app.workflow.sandbox.container_manager import ContainerManager
    manager = ContainerManager()
    assert manager is not None
    assert manager.pool_size == 5


def test_container_manager_config():
    """测试容器管理器配置"""
    from app.workflow.sandbox.container_manager import ContainerManager
    manager = ContainerManager(pool_size=3, image="python:3.12-slim")
    assert manager.pool_size == 3
    assert manager.image == "python:3.12-slim"


def test_container_manager_defaults():
    """测试默认配置"""
    from app.workflow.sandbox.container_manager import ContainerManager
    assert ContainerManager.DEFAULT_IMAGE == "python:3.11-slim"
    assert ContainerManager.DEFAULT_TIMEOUT == 30
    assert ContainerManager.DEFAULT_MEMORY_LIMIT == "256m"


def test_container_manager_methods():
    """测试方法存在"""
    from app.workflow.sandbox.container_manager import ContainerManager
    assert hasattr(ContainerManager, 'create_container')
    assert hasattr(ContainerManager, 'remove_container')
    assert hasattr(ContainerManager, 'execute_in_container')
    assert hasattr(ContainerManager, 'get_container_status')
    assert hasattr(ContainerManager, 'cleanup_work_dir')


@pytest.mark.skipif(
    True,  # 默认跳过，需要真实 Docker
    reason="需要真实 Docker 环境"
)
@pytest.mark.asyncio
async def test_create_container_real():
    """测试创建容器（需要真实 Docker）"""
    from app.workflow.sandbox.container_manager import ContainerManager
    manager = ContainerManager()
    container = await manager.create_container(name="test-sandbox")
    assert container is not None
    assert container.status == "running"
    await manager.remove_container(container)