"""文件存储服务

使用 MinIO 对象存储管理文件：
- 上传文档文件
- 获取文件内容
- 删除文件
- 管理存储桶
"""

from minio import Minio
from minio.error import S3Error
from typing import Optional
import io
from datetime import datetime, timedelta
from app.config import get_settings


settings = get_settings()


class FileService:
    """MinIO 文件存储服务"""

    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._ensure_bucket()

    def _ensure_bucket(self):
        """确保存储桶存在"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            print(f"MinIO bucket creation error: {e}")

    async def upload_file(
        self,
        content: bytes,
        filename: str,
        user_id: str,
        project_id: Optional[str] = None,
        knowledge_base_id: Optional[str] = None,
    ) -> dict:
        """上传文件到 MinIO

        Args:
            content: 文件二进制内容
            filename: 文件名
            user_id: 用户 ID
            project_id: 项目 ID（可选）
            knowledge_base_id: 知识库 ID（可选）

        Returns:
            上传结果，包含 file_path、file_size 等
        """
        # 构建存储路径
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        if knowledge_base_id:
            object_name = f"kb_{knowledge_base_id}/{timestamp}_{filename}"
        elif project_id:
            object_name = f"project_{project_id}/{timestamp}_{filename}"
        else:
            object_name = f"user_{user_id}/{timestamp}_{filename}"

        # 上传
        content_stream = io.BytesIO(content)
        self.client.put_object(
            self.bucket_name,
            object_name,
            content_stream,
            length=len(content),
        )

        return {
            "file_path": object_name,
            "filename": filename,
            "file_size": len(content),
            "bucket": self.bucket_name,
        }

    async def get_file(self, file_path: str) -> bytes:
        """获取文件内容

        Args:
            file_path: MinIO 对象路径

        Returns:
            文件二进制内容
        """
        try:
            response = self.client.get_object(self.bucket_name, file_path)
            content = response.read()
            response.close()
            response.release_conn()
            return content
        except S3Error as e:
            raise FileNotFoundError(f"File not found: {file_path}") from e

    async def delete_file(self, file_path: str):
        """删除文件

        Args:
            file_path: MinIO 对象路径
        """
        try:
            self.client.remove_object(self.bucket_name, file_path)
        except S3Error as e:
            print(f"MinIO delete error: {e}")

    async def get_file_url(self, file_path: str, expires: int = 3600) -> str:
        """获取文件临时访问 URL

        Args:
            file_path: MinIO 对象路径
            expires: 过期时间（秒）

        Returns:
            临时访问 URL
        """
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                file_path,
                expires=timedelta(seconds=expires),
            )
            return url
        except S3Error as e:
            raise FileNotFoundError(f"File not found: {file_path}") from e

    async def list_files(self, prefix: str = "") -> list:
        """列出文件

        Args:
            prefix: 路径前缀

        Returns:
            文件列表
        """
        objects = self.client.list_objects(self.bucket_name, prefix=prefix)
        return [
            {
                "name": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified,
            }
            for obj in objects
        ]


# 全局服务实例（延迟初始化）
_file_service: Optional[FileService] = None


def get_file_service() -> FileService:
    """获取文件服务实例（延迟初始化）"""
    global _file_service
    if _file_service is None:
        _file_service = FileService()
    return _file_service