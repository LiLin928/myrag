"""Docker 容器管理器

管理 OpenSandbox Docker 容器的创建、启动、停止、删除
"""

import docker
from docker.models.containers import Container
from typing import Optional, Dict, Any
import logging
import httpx
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class ContainerManager:
    """Docker 容器管理器"""

    # 默认配置
    DEFAULT_IMAGE = "opensandbox/code-interpreter:v1.0.2"
    DEFAULT_POOL_SIZE = 5
    DEFAULT_TIMEOUT = 30  # 执行超时（秒）
    DEFAULT_MEMORY_LIMIT = "256m"  # 内存限制
    DEFAULT_CPU_LIMIT = 0.5  # CPU 限制（50%）

    # Docker 连接配置（从 settings 中读取实际值，这些是备用默认值）
    DEFAULT_DOCKER_HOST = "tcp://localhost:2375"
    DEFAULT_SANDBOX_HOST = "localhost"
    DEFAULT_EXECD_PORT = 44772

    # 网络配置（已确认：网络启用）
    NETWORK_ENABLED = True  # 允许网络请求

    def __init__(
        self,
        pool_size: int = None,
        image: str = None,
        docker_host: str = None,
        sandbox_host: str = None,
        execd_port: int = None,
    ):
        """初始化容器管理器

        Args:
            pool_size: 沙箱池大小
            image: Docker 镜像名称
            docker_host: Docker 主机地址（如 tcp://192.168.137.13:2375）
            sandbox_host: OpenSandbox API 主机地址
            execd_port: OpenSandbox execd 端口
        """
        # 从配置读取默认值
        settings = get_settings()
        self.pool_size = pool_size or getattr(settings, 'SANDBOX_POOL_SIZE', None) or self.DEFAULT_POOL_SIZE
        self.image = image or getattr(settings, 'SANDBOX_IMAGE', None) or self.DEFAULT_IMAGE
        self.docker_host = docker_host or getattr(settings, 'DOCKER_HOST', None) or self.DEFAULT_DOCKER_HOST

        # OpenSandbox API 配置 - 从 settings 读取
        self.sandbox_host = sandbox_host or getattr(settings, 'SANDBOX_HOST', None) or self.DEFAULT_SANDBOX_HOST
        self.execd_port = execd_port or getattr(settings, 'SANDBOX_EXECD_PORT', None) or self.DEFAULT_EXECD_PORT

        # Docker 客户端
        self.client: Optional[docker.DockerClient] = None

        # HTTP 客户端（用于 OpenSandbox API）
        self.http_client: Optional[httpx.AsyncClient] = None

    def _init_client(self):
        """初始化 Docker 客户端"""
        try:
            logger.info(f"Connecting to Docker at: {self.docker_host}")
            self.client = docker.DockerClient(base_url=self.docker_host)
            # 测试连接
            self.client.ping()
            logger.info("Docker client connected successfully")
        except Exception as e:
            logger.error(f"Docker client initialization error: {e}")
            self.client = None

    async def _init_http_client(self):
        """初始化 HTTP 客户端（用于 OpenSandbox API）"""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=60.0)

    def get_client(self) -> Optional[docker.DockerClient]:
        """获取 Docker 客户端（延迟初始化）"""
        if self.client is None:
            self._init_client()
        return self.client

    async def execute_via_api(
        self,
        code: str,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """通过 OpenSandbox API 执行代码

        OpenSandbox 容器暴露了 execd 端口 (44772)，可以通过 HTTP API 执行代码

        Args:
            code: Python 代码
            timeout: 执行超时

        Returns:
            执行结果
        """
        await self._init_http_client()

        # 尝试多种 API 端点格式
        api_endpoints = [
            f"http://{self.sandbox_host}:{self.execd_port}/execute",
            f"http://{self.sandbox_host}:{self.execd_port}/exec",
            f"http://{self.sandbox_host}:{self.execd_port}/api/execute",
            f"http://{self.sandbox_host}:{self.execd_port}/run",
        ]

        payload = {"code": code, "timeout": timeout}

        for url in api_endpoints:
            try:
                logger.info(f"Trying OpenSandbox API: {url}")
                response = await self.http_client.post(
                    url,
                    json=payload,
                    timeout=timeout + 10,
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"OpenSandbox API success: {url}")
                    return {
                        "success": result.get("success", True),
                        "output": result.get("output", ""),
                        "error": result.get("error", ""),
                    }
                elif response.status_code != 404:
                    # 非 404 错误，说明端点存在但执行失败
                    logger.warning(f"OpenSandbox API returned {response.status_code}: {url}")
                    return {
                        "success": False,
                        "output": "",
                        "error": f"API error: {response.status_code} - {response.text}",
                    }

            except httpx.TimeoutException:
                logger.warning(f"OpenSandbox API timeout: {url}")
                continue
            except httpx.ConnectError as e:
                logger.warning(f"OpenSandbox connection error: {url} - {e}")
                continue
            except Exception as e:
                logger.warning(f"OpenSandbox API error: {url} - {e}")
                continue

        # 所有端点都失败
        logger.error(f"All OpenSandbox API endpoints failed. Host: {self.sandbox_host}, Port: {self.execd_port}")
        return {
            "success": False,
            "output": "",
            "error": f"Cannot connect to OpenSandbox at {self.sandbox_host}:{self.execd_port}. Please check if the sandbox container is running.",
        }

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