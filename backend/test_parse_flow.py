"""测试解析流程 - 完整诊断"""

import asyncio
import sys
import os
import tempfile
from pathlib import Path

# 设置路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def test_parse_flow():
    """测试完整的解析流程"""
    print("=" * 60)
    print("测试解析流程")
    print("=" * 60)

    from sqlalchemy import create_engine, text
    from app.config import get_settings
    from app.services.file_service import get_file_service
    from app.rag.extractor.factory import ExtractorFactory

    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://'))

    # Step 1: 获取文档信息
    print("\n[1] 获取文档信息...")
    with engine.connect() as conn:
        result = conn.execute(
            text('SELECT id, file_path, filename FROM documents WHERE knowledge_base_id = :kb_id ORDER BY created_at DESC LIMIT 1'),
            {'kb_id': '4f761b48-d7c0-4b0d-b042-a0db528bde24'}
        )
        doc = result.fetchone()

        if not doc:
            print("❌ 没有找到文档")
            return

        print(f"✓ 文档ID: {doc[0]}")
        print(f"✓ 文件路径: {doc[1]}")
        print(f"✓ 文件名: {doc[2]}")

        file_path = doc[1]
        document_id = doc[0]

    # Step 2: 从MinIO下载文件
    print("\n[2] 从MinIO下载文件...")
    file_service = get_file_service()

    try:
        content = await file_service.get_file(file_path)
        print(f"✓ 文件下载成功: {len(content)} bytes")

        # 保存到临时文件
        file_ext = Path(file_path).suffix
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
        temp_file.write(content)
        temp_file.close()

        local_path = temp_file.name
        print(f"✓ 临时文件: {local_path}")

    except Exception as e:
        print(f"❌ 文件下载失败: {e}")
        return

    # Step 3: 获取解析器
    print("\n[3] 获取解析器...")
    extractor = ExtractorFactory.get_extractor(local_path)

    if not extractor:
        print(f"❌ 没有找到支持的解析器 (文件类型: {file_ext})")
        os.unlink(local_path)
        return

    print(f"✓ 使用解析器: {extractor.__class__.__name__}")

    # Step 4: 执行解析
    print("\n[4] 执行解析...")
    try:
        blocks = await extractor.extract(local_path)
        print(f"✓ 解析成功: {len(blocks)} 个内容块")

        if blocks:
            print("\n前3个内容块:")
            for i, block in enumerate(blocks[:3]):
                block_type = block.get('type', 'unknown') if isinstance(block, dict) else getattr(block, 'type', 'unknown')
                content_preview = (block.get('content', '') if isinstance(block, dict) else getattr(block, 'content', ''))[:50]
                print(f"  Block {i}: type={block_type}, content={content_preview}...")
        else:
            print("⚠️ 没有提取到任何内容块")

    except Exception as e:
        print(f"❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()
        os.unlink(local_path)
        return

    # Step 5: 构建parsed_data
    print("\n[5] 构建parsed_data...")
    parsed_data = {
        "text": "",
        "sections": [],
        "tables": [],
        "page_number": 1,
    }

    all_text = []
    for block in blocks:
        block_type = block.get('type') if isinstance(block, dict) else getattr(block, 'type', None)

        if block_type == "text":
            content = block.get('content') if isinstance(block, dict) else getattr(block, 'content', '')
            all_text.append(content)
        elif block_type == "table":
            content = block.get('content') if isinstance(block, dict) else getattr(block, 'content', '')
            parsed_data["tables"].append({"content": content, "page": 1})

    parsed_data["text"] = "\n\n".join(all_text)
    print(f"✓ 文本长度: {len(parsed_data['text'])} 字符")
    print(f"✓ 表格数量: {len(parsed_data['tables'])}")

    # Step 6: 测试分块
    print("\n[6] 测试分块...")
    from app.rag.splitter.mixed_splitter import MixedSplitter

    splitter = MixedSplitter()
    chunks = splitter.split(parsed_data, "auto")
    print(f"✓ 生成分块: {len(chunks)} 个")

    if chunks:
        print("\n前3个分块:")
        for i, chunk in enumerate(chunks[:3]):
            print(f"  Chunk {i}: {chunk.get('content', '')[:50]}...")

    # 清理临时文件
    os.unlink(local_path)

    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

    if len(blocks) == 0:
        print("\n⚠️ 问题: 解析器没有提取任何内容")
        print("建议: 检查python-docx是否正确安装，文件是否损坏")

    elif len(chunks) == 0:
        print("\n⚠️ 问题: 分块器没有生成任何分块")
        print("建议: 检查parsed_data格式，调整分块策略")

    else:
        print("\n✓ 解析流程正常，问题可能在数据库插入步骤")
        print("建议: 启动Worker，查看完整日志")

if __name__ == "__main__":
    asyncio.run(test_parse_flow())