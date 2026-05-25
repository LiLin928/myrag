# backend/tests/tasks/test_extractor.py

import pytest
import tempfile
from pathlib import Path

from app.rag.extractor.factory import ExtractorFactory
from app.rag.extractor.text_extractor import TextExtractor


@pytest.mark.asyncio
async def test_text_extractor():
    """测试纯文本解析器"""
    # 创建临时文件（明确指定 UTF-8 编码）
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("第一段内容\n\n第二段内容\n\n第三段内容")
        temp_path = f.name

    extractor = TextExtractor()
    blocks = await extractor.extract(temp_path)

    assert len(blocks) == 3
    assert blocks[0]["content"] == "第一段内容"
    assert blocks[1]["content"] == "第二段内容"

    # 清理
    Path(temp_path).unlink()


@pytest.mark.asyncio
async def test_text_extractor_markdown():
    """测试 Markdown 解析"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Title\n\n## Section\n\nContent here")
        temp_path = f.name

    extractor = TextExtractor()
    blocks = await extractor.extract(temp_path)

    assert len(blocks) >= 1
    assert "# Title" in blocks[0]["content"]

    Path(temp_path).unlink()


def test_extractor_factory_txt():
    """测试工厂获取 txt 解析器"""
    extractor = ExtractorFactory.get_extractor("test.txt")
    assert extractor is not None
    assert isinstance(extractor, TextExtractor)


def test_extractor_factory_md():
    """测试工厂获取 md 解析器"""
    extractor = ExtractorFactory.get_extractor("test.md")
    assert extractor is not None
    assert isinstance(extractor, TextExtractor)


def test_extractor_factory_unsupported():
    """测试不支持文件类型"""
    extractor = ExtractorFactory.get_extractor("test.xyz")
    assert extractor is None


def test_extractor_factory_supports():
    """测试支持检查"""
    assert ExtractorFactory.supports("test.txt")
    assert ExtractorFactory.supports("test.md")
    assert not ExtractorFactory.supports("test.xyz")


def test_text_extractor_supports_file_type():
    """测试 supports_file_type 方法"""
    assert TextExtractor.supports_file_type(".txt")
    assert TextExtractor.supports_file_type(".md")
    assert not TextExtractor.supports_file_type(".pdf")