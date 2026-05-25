"""沙箱池管理器

预创建 Docker 容器池，避免每次执行都创建容器：
- 预创建 pool_size 个容器
- acquire() 获取可用容器
- release() 归还容器并清理工作目录
- execute_code() 快速执行代码
"""

import asyncio
from typing import Optional, Dict, Any, List
import json

from app.workflow.sandbox.container_manager import ContainerManager


class SandboxPool:
    """沙箱池管理器"""

    def __init__(
        self,
        pool_size: int = 5,
        image: str = None,
    ):
        """初始化沙箱池

        Args:
            pool_size: 沙箱池大小
            image: Docker 镜像
        """
        self.pool_size = pool_size
        self.image = image

        # 容器管理器
        self.container_manager = ContainerManager(pool_size=pool_size, image=image)

        # 容器池
        self.available_containers: List = []
        self.in_use_containers: List = []

        # 初始化锁
        self._lock = asyncio.Lock()

        # 初始化完成标志
        self._initialized = False

    async def initialize(self):
        """初始化容器池

        预创建 pool_size 个容器
        """
        if self._initialized:
            return

        async with self._lock:
            for i in range(self.pool_size):
                container = await self.container_manager.create_container(
                    name=f"myrag-sandbox-{i}"
                )
                if container:
                    self.available_containers.append(container)

            self._initialized = True

    async def acquire(self) -> Optional[Any]:
        """获取可用容器

        Returns:
            Container 实例，无可用则返回 None
        """
        async with self._lock:
            if not self.available_containers:
                # 池中没有可用容器，创建新的
                container = await self.container_manager.create_container()
                if container:
                    self.in_use_containers.append(container)
                    return container
                return None

            container = self.available_containers.pop(0)
            self.in_use_containers.append(container)
            return container

    async def release(self, container):
        """释放容器

        清理工作目录后归还池中

        Args:
            container: Container 实例
        """
        async with self._lock:
            # 清理工作目录
            await self.container_manager.cleanup_work_dir(container)

            # 从 in_use 移除
            if container in self.in_use_containers:
                self.in_use_containers.remove(container)

            # 归还池中
            self.available_containers.append(container)

    async def execute_code(
        self,
        code: str,
        timeout: int = 30,
        packages: List[str] = None,
    ) -> Dict[str, Any]:
        """执行代码

        Args:
            code: Python 代码
            timeout: 执行超时
            packages: 需要安装的包（可选）

        Returns:
            执行结果
        """
        # 确保池已初始化
        if not self._initialized:
            await self.initialize()

        # 获取容器
        container = await self.acquire()
        if not container:
            return {
                "success": False,
                "output": "",
                "error": "No available container",
            }

        try:
            # 安装额外包（如有）
            if packages:
                await self.container_manager.install_packages(container, packages)

            # 执行代码
            result = await self.container_manager.execute_in_container(
                container=container,
                code=code,
                timeout=timeout,
            )

            return result

        finally:
            # 释放容器
            await self.release(container)

    async def execute_skill(
        self,
        skill_code: str,
        skill_input: Dict[str, Any],
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """执行 Skill

        Skills 是预定义的代码模板，接收输入参数

        Args:
            skill_code: Skill 代码
            skill_input: 输入参数
            timeout: 执行超时

        Returns:
            执行结果
        """
        # 包装 Skill 执行
        wrapped_code = f'''
import json

skill_input = json.loads('{json.dumps(skill_input)}')

{skill_code}

result = execute(skill_input)
print(json.dumps(result))
'''

        return await self.execute_code(wrapped_code, timeout)

    async def shutdown(self):
        """关闭沙箱池

        停止并删除所有容器
        """
        async with self._lock:
            # 删除可用容器
            for container in self.available_containers:
                await self.container_manager.remove_container(container)

            # 删除使用中的容器
            for container in self.in_use_containers:
                await self.container_manager.remove_container(container)

            self.available_containers = []
            self.in_use_containers = []
            self._initialized = False

    def get_pool_status(self) -> Dict[str, int]:
        """获取池状态

        Returns:
            {"available": n, "in_use": n, "total": n}
        """
        return {
            "available": len(self.available_containers),
            "in_use": len(self.in_use_containers),
            "total": self.pool_size,
        }


# 全局沙箱池实例（延迟初始化）
_sandbox_pool: Optional[SandboxPool] = None


def get_sandbox_pool() -> SandboxPool:
    """获取沙箱池实例（延迟初始化）"""
    global _sandbox_pool
    if _sandbox_pool is None:
        _sandbox_pool = SandboxPool(pool_size=5)
    return _sandbox_pool