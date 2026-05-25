# backend/tests/services/test_file_service.py

import pytest
from unittest.mock import MagicMock, patch


def test_file_service_class_exists():
    """测试 FileService 类存在"""
    from app.services.file_service import FileService
    assert FileService is not None


def test_file_service_methods():
    """测试 FileService 方法签名"""
    from app.services.file_service import FileService

    # 检查方法存在
    assert hasattr(FileService, 'upload_file')
    assert hasattr(FileService, 'get_file')
    assert hasattr(FileService, 'delete_file')
    assert hasattr(FileService, 'get_file_url')
    assert hasattr(FileService, 'list_files')


def test_upload_file_mocked():
    """测试文件上传（使用 mock）"""
    with patch('app.services.file_service.Minio') as mock_minio:
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.put_object = MagicMock()
        mock_minio.return_value = mock_client

        from app.services.file_service import FileService
        service = FileService()

        file_content = b"test content"
        filename = "test.pdf"
        user_id = "user-001"

        import asyncio
        result = asyncio.run(service.upload_file(file_content, filename, user_id))

        assert result is not None
        assert "file_path" in result
        assert result["filename"] == filename


def test_get_file_mocked():
    """测试文件获取（使用 mock）"""
    with patch('app.services.file_service.Minio') as mock_minio:
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_response = MagicMock()
        mock_response.read.return_value = b"test content"
        mock_response.close = MagicMock()
        mock_response.release_conn = MagicMock()
        mock_client.get_object.return_value = mock_response
        mock_minio.return_value = mock_client

        from app.services.file_service import FileService
        service = FileService()

        import asyncio
        file_path = "user_1/test.pdf"
        content = asyncio.run(service.get_file(file_path))

        assert content == b"test content"


def test_delete_file_mocked():
    """测试文件删除（使用 mock）"""
    with patch('app.services.file_service.Minio') as mock_minio:
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.remove_object = MagicMock()
        mock_minio.return_value = mock_client

        from app.services.file_service import FileService
        service = FileService()

        import asyncio
        file_path = "user_1/test.pdf"
        asyncio.run(service.delete_file(file_path))

        mock_client.remove_object.assert_called_once()


def test_get_file_url_mocked():
    """测试获取临时 URL（使用 mock）"""
    with patch('app.services.file_service.Minio') as mock_minio:
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.presigned_get_object.return_value = "http://test.url/file"
        mock_minio.return_value = mock_client

        from app.services.file_service import FileService
        service = FileService()

        import asyncio
        file_path = "user_1/test.pdf"
        url = asyncio.run(service.get_file_url(file_path))

        assert url == "http://test.url/file"


def test_list_files_mocked():
    """测试列出文件（使用 mock）"""
    with patch('app.services.file_service.Minio') as mock_minio:
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_obj = MagicMock()
        mock_obj.object_name = "test.pdf"
        mock_obj.size = 1024
        mock_obj.last_modified = None
        mock_client.list_objects.return_value = [mock_obj]
        mock_minio.return_value = mock_client

        from app.services.file_service import FileService
        service = FileService()

        import asyncio
        files = asyncio.run(service.list_files("user_1/"))

        assert len(files) == 1
        assert files[0]["name"] == "test.pdf"


def test_get_file_service():
    """测试获取文件服务实例"""
    from app.services.file_service import get_file_service
    assert get_file_service is not None