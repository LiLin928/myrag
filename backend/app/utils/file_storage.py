"""文件存储工具

管理技能文件在服务器文件系统上的存储
"""

import os
import hashlib
import shutil
from pathlib import Path
from typing import Dict, List, Optional, BinaryIO
import aiofiles
import asyncio

from app.config import get_settings

settings = get_settings()


class FileStorage:
    """文件存储管理器"""

    def __init__(self):
        self.base_path = Path(settings.SKILL_STORAGE_PATH)
        self._ensure_base_path()

    def _ensure_base_path(self):
        """确保基础存储目录存在"""
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _validate_path(self, skill_dir: Path, file_path: str) -> Path:
        """Validate path to prevent traversal attacks"""
        full_path = (skill_dir / file_path).resolve()
        if not str(full_path).startswith(str(skill_dir.resolve())):
            raise ValueError(f"Path traversal detected: {file_path}")
        return full_path

    def get_skill_directory(self, internal_name: str) -> Path:
        """获取技能目录路径"""
        return self.base_path / internal_name

    def ensure_skill_directory(self, internal_name: str) -> Path:
        """确保技能目录存在"""
        skill_dir = self.get_skill_directory(internal_name)
        skill_dir.mkdir(parents=True, exist_ok=True)
        return skill_dir

    async def create_file(
        self,
        internal_name: str,
        file_path: str,
        content: str | bytes,
    ) -> Dict:
        """创建文件

        Args:
            internal_name: 技能内部名称
            file_path: 文件相对路径（如 main.py, scripts/helper.sh）
            content: 文件内容（字符串或字节）

        Returns:
            {path, size, hash}
        """
        skill_dir = self.ensure_skill_directory(internal_name)
        full_path = self._validate_path(skill_dir, file_path)

        # 确保父目录存在
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        if isinstance(content, str):
            async with aiofiles.open(full_path, 'w', encoding='utf-8') as f:
                await f.write(content)
        else:
            async with aiofiles.open(full_path, 'wb') as f:
                await f.write(content)

        # 计算哈希和大小
        file_hash = await self._compute_hash(full_path)
        file_size = full_path.stat().st_size

        return {
            "path": file_path,
            "size": file_size,
            "hash": file_hash,
        }

    async def read_file(self, internal_name: str, file_path: str) -> str:
        """读取文件内容"""
        skill_dir = self.get_skill_directory(internal_name)
        full_path = self._validate_path(skill_dir, file_path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
            return await f.read()

    async def read_file_binary(self, internal_name: str, file_path: str) -> bytes:
        """读取二进制文件内容"""
        skill_dir = self.get_skill_directory(internal_name)
        full_path = self._validate_path(skill_dir, file_path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        async with aiofiles.open(full_path, 'rb') as f:
            return await f.read()

    async def update_file(
        self,
        internal_name: str,
        file_path: str,
        content: str | bytes,
    ) -> Dict:
        """更新文件内容"""
        return await self.create_file(internal_name, file_path, content)

    async def delete_file(self, internal_name: str, file_path: str):
        """删除文件"""
        skill_dir = self.get_skill_directory(internal_name)
        full_path = self._validate_path(skill_dir, file_path)

        if full_path.exists():
            full_path.unlink()

    async def list_files(self, internal_name: str) -> List[Dict]:
        """列出技能所有文件"""
        skill_dir = self.get_skill_directory(internal_name)

        if not skill_dir.exists():
            return []

        files = []
        for path in skill_dir.rglob('*'):
            if path.is_file():
                relative_path = str(path.relative_to(skill_dir))
                file_hash = await self._compute_hash(path)
                file_size = path.stat().st_size
                files.append({
                    "path": relative_path,
                    "hash": file_hash,
                    "size": file_size,
                })

        return files

    async def delete_skill_directory(self, internal_name: str):
        """删除技能整个目录"""
        skill_dir = self.get_skill_directory(internal_name)
        if skill_dir.exists():
            await asyncio.to_thread(shutil.rmtree, skill_dir)

    async def _compute_hash(self, file_path: Path) -> str:
        """计算文件 SHA256 哈希"""
        sha256 = hashlib.sha256()
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_file_type(self, file_path: str) -> str:
        """根据文件扩展名推断文件类型"""
        ext = Path(file_path).suffix.lower()
        type_map = {
            '.py': 'python',
            '.sh': 'shell',
            '.bash': 'shell',
            '.md': 'markdown',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json',
            '.txt': 'text',
            '.toml': 'toml',
            '.ini': 'ini',
            '.cfg': 'config',
        }
        return type_map.get(ext, 'unknown')


# 全局实例
file_storage = FileStorage()
