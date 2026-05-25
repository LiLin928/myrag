"""测试文档解析和分块流程

直接调用解析器和分块器，验证数据是否正确生成
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.rag.extractor.factory import ExtractorFactory
from app.rag.splitter.mixed_splitter import MixedSplitter


async def test_parse_and_chunk(file_path: str):
    """测试解析和分块"""

    print(f"\n=== 测试文件: {file_path} ===")

    # 1. 获取解析器
    extractor = ExtractorFactory.get_extractor(file_path)
    if not extractor:
        print(f"ERROR: 不支持的文件类型")
        return

    print(f"解析器: {extractor.__class__.__name__}")

    # 2. 执行解析
    blocks = await extractor.extract(file_path)
    print(f"解析结果: {len(blocks)} 个内容块")

    # 3. 构建 parsed_data
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
            all_text.append(content if content else str(block))
        elif block_type == "table":
            content = block.get('content') if isinstance(block, dict) else getattr(block, 'content', '')
            parsed_data["tables"].append({"content": content, "page": 1})

    parsed_data["text"] = "\n\n".join(all_text)

    print(f"\n=== parsed_data ===")
    print(f"text 长度: {len(parsed_data['text'])}")
    print(f"text 预览: {parsed_data['text'][:200] if parsed_data['text'] else 'EMPTY'}")
    print(f"tables 数量: {len(parsed_data['tables'])}")

    # 4. 执行分块
    splitter = MixedSplitter()
    chunks = splitter.split(parsed_data, "auto")

    print(f"\n=== 分块结果 ===")
    print(f"chunks 数量: {len(chunks)}")

    if chunks:
        print(f"第一个 chunk:")
        print(f"  clause_id: {chunks[0].get('clause_id', 'NO ID')}")
        print(f"  content 预览: {chunks[0].get('content', 'NO CONTENT')[:100]}")

        print(f"\n所有 chunks 的 clause_id:")
        for i, chunk in enumerate(chunks):
            print(f"  chunk_{i}: clause_id={chunk.get('clause_id')}, content_len={len(chunk.get('content', ''))}")
    else:
        print("WARNING: 没有生成任何分块!")

    return chunks


if __name__ == "__main__":
    # 测试一个简单的文本文件
    test_file = sys.argv[1] if len(sys.argv) > 1 else None

    if not test_file:
        # 创建一个临时测试文件
        import tempfile
        test_content = """
这是测试文档的标题

第一章：概述
这是一个测试文档，用于验证解析和分块功能是否正常工作。
文档包含多个段落和章节结构。

第二章：详细说明
本章节包含更多详细内容。
测试内容包括：
- 列表项1
- 列表项2
- 列表项3

第三章：总结
测试完成。
"""

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_file.write(test_content)
        temp_file.close()
        test_file = temp_file.name
        print(f"创建临时测试文件: {test_file}")

    asyncio.run(test_parse_and_chunk(test_file))