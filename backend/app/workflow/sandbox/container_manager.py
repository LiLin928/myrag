"""Docker 容器管理器

管理 OpenSandbox Docker 容器的创建、启动、停止、删除
"""

import docker
from docker.models.containers import Container
from typing import Optional, Dict, Any
from app.config import get_settings

settings = get_settings()


class ContainerManager:
    """Docker 容器管理器"""

    # 默认配置
    DEFAULT_IMAGE = "python:3.11-slim"
    DEFAULT_POOL_SIZE = 5
    DEFAULT_TIMEOUT = 30  # 执行超时（秒）
    DEFAULT_MEMORY_LIMIT = "256m"  # 内存限制
    DEFAULT_CPU_LIMIT = 0.5  # CPU 限制（50%）

    # 网络配置（已确认：网络启用）
    NETWORK_ENABLED = True  # 允许网络请求

    def __init__(
        self,
        pool_size: int = None,
        image: str = None,
    ):
        """初始化容器管理器

        Args:
            pool_size: 沙箱池大小
            image: Docker 镜像名称
        """
        self.pool_size = pool_size or settings.SANDBOX_POOL_SIZE or self.DEFAULT_POOL_SIZE
        self.image = image or self.DEFAULT_IMAGE

        # Docker 客户端
        self.client: Optional[docker.DockerClient] = None

    def _init_client(self):
        """初始化 Docker 客户端"""
        try:
            self.client = docker.from_env()
        except docker.errors.DockerException as e:
            print(f"Docker client initialization error: {e}")
            self.client = None

    def get_client(self) -> Optional[docker.DockerClient]:
        """获取 Docker 客户端（延迟初始化）"""
        if self.client is None:
            self._init_client()
        return self.client

    async def create_container(
        self,
        name: Optional[str] = None,
        work_dir: str = "/sandbox",
    ) -> Optional[Container]:
        """创建沙箱容器

        Args:
            name: 容器名称（可选）
            work_dir: 工作目录路径

        Returns:
            Container 实例
        """
        client = self.get_client()
        if not client:
            raise RuntimeError("Docker client not initialized")

        container_config = {
            "image": self.image,
            "detach": True,
            "working_dir": work_dir,
            "command": "tail -f /dev/null",  # 保持容器运行
            "mem_limit": self.DEFAULT_MEMORY_LIMIT,
            "cpu_quota": int(self.DEFAULT_CPU_LIMIT * 100000),
            # 网络配置（网络启用）
            "network_disabled": False,  # 允许网络
            # 安全配置
            "security_opt": ["no-new-privileges"],
            "cap_drop": ["ALL"],
            # 预装常用包
            "environment": {
                "PIP_PACKAGES": "requests httpx numpy pandas",
            }
        }

        if name:
            container_config["name"] = name

        try:
            container = client.containers.create(**container_config)
            container.start()
            return container

        except docker.errors.APIError as e:
            print(f"Container creation error: {e}")
            return None

    async def remove_container(self, container: Container):
        """删除容器

        Args:
            container: Container 实例
        """
        try:
            container.stop()
            container.remove(force=True)
        except docker.errors.APIError as e:
            print(f"Container removal error: {e}")

    async def execute_in_container(
        self,
        container: Container,
        code: str,
        timeout: int = None,
    ) -> Dict[str, Any]:
        """在容器中执行代码

        Args:
            container: Container 实例
            code: Python 代码
            timeout: 执行超时

        Returns:
            执行结果：{"success": bool, "output": str, "error": str}
        """
        timeout = timeout or self.DEFAULT_TIMEOUT

        # 创建执行脚本
        exec_script = f'''
import sys
import io
import json

# 捕获标准输出
_stdout = io.StringIO()
sys.stdout = _stdout

code = """{code}"""

try:
    # 预装包导入
    try:
        import requests
        import httpx
    except ImportError:
        pass

    # 执行用户代码
    exec(code, {{'__name__': '__main__'}})

    output = _stdout.getvalue()
    print(json.dumps({
        "success": True,
        "output": output,
        "error": None
    }))

except Exception as e:
    print(json.dumps({
        "success": False,
        "output": "",
        "error": str(e)
    }))
'''

        try:
            # 执行代码
            exit_code, output = container.exec_run(
                cmd=["python", "-c", exec_script],
                timeout=timeout,
            )

            return {
                "success": exit_code == 0,
                "output": output.decode('utf-8') if output else "",
                "exit_code": exit_code,
            }

        except docker.errors.APIError as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
            }

    def get_container_status(self, container: Container) -> str:
        """获取容器状态

        Args:
            container: Container 实例

        Returns:
            状态字符串（running/exited/paused）
        """
        container.reload()
        return container.status

    async def cleanup_work_dir(self, container: Container):
        """清理工作目录

        Args:
            container: Container 实例
        """
        try:
            container.exec_run(cmd="rm -rf /sandbox/*")
        except docker.errors.APIError as e:
            print(f"Work dir cleanup error: {e}")

    async def install_packages(self, container: Container, packages: list):
        """安装 Python 包

        Args:
            container: Container 实例
            packages: 包列表
        """
        package_str = " ".join(packages)
        try:
            container.exec_run(cmd=f"pip install {package_str}", timeout=60)
        except docker.errors.APIError as e:
            print(f"Package installation error: {e}")