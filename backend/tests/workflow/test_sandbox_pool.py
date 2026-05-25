# backend/tests/workflow/test_sandbox_pool.py

import pytest
from app.workflow.sandbox.sandbox_pool import SandboxPool, get_sandbox_pool


def test_sandbox_pool_init():
    """测试沙箱池初始化"""
    pool = SandboxPool(pool_size=3)
    assert pool.pool_size == 3
    assert pool.available_containers == []


def test_sandbox_pool_config():
    """测试沙箱池配置"""
    pool = SandboxPool(pool_size=10, image="python:3.12-slim")
    assert pool.pool_size == 10
    assert pool.image == "python:3.12-slim"


def test_sandbox_pool_methods():
    """测试方法存在"""
    pool = SandboxPool()
    assert hasattr(pool, 'initialize')
    assert hasattr(pool, 'acquire')
    assert hasattr(pool, 'release')
    assert hasattr(pool, 'execute_code')
    assert hasattr(pool, 'execute_skill')
    assert hasattr(pool, 'shutdown')
    assert hasattr(pool, 'get_pool_status')


def test_get_pool_status():
    """测试获取池状态"""
    pool = SandboxPool(pool_size=5)
    pool.available_containers = []
    pool.in_use_containers = []

    status = pool.get_pool_status()

    assert status["available"] == 0
    assert status["in_use"] == 0
    assert status["total"] == 5


def test_get_sandbox_pool():
    """测试获取沙箱池实例"""
    pool = get_sandbox_pool()
    assert pool is not None
    assert isinstance(pool, SandboxPool)