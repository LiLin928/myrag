"""沙箱池管理器

使用 OpenSandbox SDK 执行代码
"""

import asyncio
from typing import Optional, Dict, Any, List
import json
import logging
import subprocess
import sys

from app.config import get_settings

logger = logging.getLogger(__name__)


class SandboxPool:
    """沙箱池管理器 - 使用 OpenSandbox SDK"""

    def __init__(
        self,
        pool_size: int = 5,
        use_local: bool = False,
    ):
        """初始化沙箱池

        Args:
            pool_size: 沙箱池大小（SDK 模式下不使用）
            use_local: 是否使用本地 Python 执行
        """
        self.pool_size = pool_size
        self.use_local = use_local
        self._initialized = False
        self._sandbox = None  # OpenSandbox 实例

    async def initialize(self):
        """初始化沙箱服务"""
        if self._initialized:
            return

        settings = get_settings()

        if self.use_local:
            logger.info("SandboxPool initialized with LOCAL execution mode")
        else:
            # 使用 OpenSandbox SDK
            try:
                logger.info(f"Initializing OpenSandbox SDK: {settings.SANDBOX_HOST}:{settings.SANDBOX_PORT}")

                from opensandbox import SandboxSync
                from opensandbox.config import ConnectionConfigSync

                config = ConnectionConfigSync(
                    domain=f"{settings.SANDBOX_HOST}:{settings.SANDBOX_PORT}",
                    api_key=settings.SANDBOX_API_KEY,
                )

                # 创建沙箱实例 - 在线程池中运行以避免阻塞
                def create_sandbox():
                    return SandboxSync.create(
                        settings.SANDBOX_IMAGE,
                        connection_config=config,
                    )

                loop = asyncio.get_event_loop()
                self._sandbox = await asyncio.wait_for(
                    loop.run_in_executor(None, create_sandbox),
                    timeout=60
                )
                logger.info(f"OpenSandbox SDK initialized successfully")
            except asyncio.TimeoutError:
                logger.error("OpenSandbox SDK initialization timeout")
                self.use_local = True
                logger.info("Falling back to LOCAL execution mode due to timeout")
            except Exception as e:
                logger.error(f"OpenSandbox SDK initialization failed: {e}")
                # 回退到本地模式
                self.use_local = True
                logger.info("Falling back to LOCAL execution mode")

        self._initialized = True

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
        logger.info(f"execute_code called, initialized={self._initialized}, use_local={self.use_local}")

        if not self._initialized:
            await self.initialize()
            logger.info(f"After initialize: use_local={self.use_local}")

        if self.use_local:
            logger.info("Executing with LOCAL mode")
            return await self._execute_local(code, timeout)

        # 使用 OpenSandbox SDK 执行
        logger.info("Executing with SDK mode")
        return await self._execute_via_sdk(code, timeout)

    async def _execute_local(
        self,
        code: str,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """本地 Python 直接执行"""
        import io

        stdout_capture = io.StringIO()

        try:
            async def run_in_subprocess():
                script = f'''
import sys
import io
import json

_stdout = io.StringIO()
sys.stdout = _stdout

try:
    exec("""
{code}
""")
    output = _stdout.getvalue()
    print(json.dumps({{"success": True, "output": output, "error": None}}))
except Exception as e:
    print(json.dumps({{"success": False, "output": "", "error": str(e)}}))
'''

                process = await asyncio.create_subprocess_exec(
                    sys.executable, '-c', script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout
                    )

                    result_str = stdout.decode('utf-8') if stdout else ''
                    if result_str:
                        try:
                            return json.loads(result_str.strip())
                        except json.JSONDecodeError:
                            return {"success": False, "output": result_str, "error": "Invalid JSON output"}

                    error = stderr.decode('utf-8') if stderr else 'No output'
                    return {"success": False, "output": "", "error": error}

                except asyncio.TimeoutError:
                    process.kill()
                    return {"success": False, "output": "", "error": "Execution timeout"}

            return await run_in_subprocess()

        except Exception as e:
            logger.error(f"Local execution error: {e}")
            return {"success": False, "output": "", "error": str(e)}

    async def _execute_via_sdk(
        self,
        code: str,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """通过 OpenSandbox SDK 执行代码"""
        if self._sandbox is None:
            logger.error("OpenSandbox not initialized")
            return {
                "success": False,
                "output": "",
                "error": "OpenSandbox not initialized",
            }

        try:
            logger.info(f"Starting OpenSandbox SDK execution, code length: {len(code)}")
            logger.info(f"Code content (first 500 chars): {code[:500] if len(code) > 500 else code}")

            # 在异步环境中调用同步 SDK
            def run_sync():
                logger.info("run_sync started")
                # 写入脚本文件并执行（推荐方式）
                script_name = "user_code.py"
                try:
                    self._sandbox.files.write_file(script_name, code)
                    logger.info(f"Script written to {script_name}")
                except Exception as write_err:
                    logger.error(f"Failed to write script: {write_err}")
                    return {"success": False, "output": "", "error": f"Write file error: {write_err}"}

                # 执行脚本
                try:
                    result = self._sandbox.commands.run(f"python3 {script_name}")
                    logger.info(f"Script executed, result type: {type(result)}")
                    logger.info(f"Result has logs: {hasattr(result, 'logs')}")
                except Exception as exec_err:
                    logger.error(f"Failed to execute script: {exec_err}")
                    return {"success": False, "output": "", "error": f"Execute error: {exec_err}"}

                stdout_text = ""
                stderr_text = ""

                try:
                    if hasattr(result, 'logs') and result.logs:
                        logger.info(f"logs type: {type(result.logs)}")
                        if hasattr(result.logs, 'stdout'):
                            for msg in result.logs.stdout:
                                stdout_text += msg.text
                        if hasattr(result.logs, 'stderr'):
                            for msg in result.logs.stderr:
                                stderr_text += msg.text
                    else:
                        logger.warning("No logs attribute in result")
                except Exception as log_err:
                    logger.error(f"Error reading logs: {log_err}")

                logger.info(f"stdout length: {len(stdout_text)}, content: {stdout_text[:200] if stdout_text else 'empty'}")
                logger.info(f"stderr length: {len(stderr_text)}, content: {stderr_text[:200] if stderr_text else 'empty'}")

                if stdout_text:
                    try:
                        parsed = json.loads(stdout_text.strip())
                        logger.info(f"Parsed JSON result: {parsed}")
                        return parsed
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON decode error: {e}")
                        # 如果不是 JSON，直接返回输出
                        return {"success": True, "output": stdout_text, "error": ""}
                elif stderr_text:
                    return {"success": False, "output": "", "error": stderr_text}
                else:
                    logger.warning("Both stdout and stderr are empty!")
                    return {"success": False, "output": "", "error": "Empty output from sandbox"}

            # 在线程池中运行同步代码
            loop = asyncio.get_event_loop()
            logger.info("Submitting to thread pool")
            result = await loop.run_in_executor(None, run_sync)
            logger.info(f"Thread pool completed: {result}")
            return result

        except Exception as e:
            logger.error(f"OpenSandbox SDK execution error: {e}")
            return {"success": False, "output": "", "error": str(e)}

    async def execute_skill(
        self,
        skill_code: str,
        skill_input: Dict[str, Any],
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """执行 Skill"""
        wrapped_code = '''
import json

skill_input = json.loads('__SKILL_INPUT__')

__SKILL_CODE__

result = execute(skill_input)
print(json.dumps(result))
'''
        wrapped_code = wrapped_code.replace("__SKILL_INPUT__", json.dumps(skill_input))
        wrapped_code = wrapped_code.replace("__SKILL_CODE__", skill_code)

        return await self.execute_code(wrapped_code, timeout)

    async def shutdown(self):
        """关闭沙箱池"""
        if self._sandbox:
            try:
                self._sandbox.kill()
                self._sandbox.close()
            except Exception as e:
                logger.warning(f"Error closing sandbox: {e}")
        self._initialized = False

    def get_pool_status(self) -> Dict[str, int]:
        """获取池状态"""
        return {
            "available": self.pool_size,
            "in_use": 0,
            "total": self.pool_size,
        }


# 全局沙箱池实例
_sandbox_pool: Optional[SandboxPool] = None


def get_sandbox_pool() -> SandboxPool:
    """获取沙箱池实例"""
    global _sandbox_pool
    if _sandbox_pool is None:
        from app.config import get_settings
        settings = get_settings()

        sandbox_mode = getattr(settings, 'SANDBOX_MODE', 'server')

        if sandbox_mode == 'local':
            _sandbox_pool = SandboxPool(pool_size=5, use_local=True)
            logger.info("SandboxPool initialized with LOCAL execution mode")
        else:
            _sandbox_pool = SandboxPool(pool_size=5, use_local=False)
            logger.info("SandboxPool initialized with OpenSandbox SDK mode")
    return _sandbox_pool