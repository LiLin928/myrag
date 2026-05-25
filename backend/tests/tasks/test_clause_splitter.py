# backend/tests/tasks/test_clause_splitter.py

import pytest
from app.rag.splitter.clause_splitter import ClauseSplitter, ClauseBlock


def test_clause_splitter_init():
    """测试初始化"""
    splitter = ClauseSplitter()
    assert splitter is not None


def test_detect_clause_title():
    """测试条款标题检测"""
    splitter = ClauseSplitter()

    # 中文条款
    title = splitter._detect_clause_title("第一条 总则\n本合同依据...")
    assert title == "第一条 总则"

    # 数字条款
    title = splitter._detect_clause_title("第1条 定义\n...")
    assert title is not None

    # 无条款标题
    title = splitter._detect_clause_title("普通文本，无条款标题")
    assert title is None


def test_detect_clause_type():
    """测试条款类型检测"""
    splitter = ClauseSplitter()

    # 定义条款
    type_ = splitter._detect_clause_type("本合同中，以下术语的定义如下...")
    assert type_ == "定义"

    # 义务条款
    type_ = splitter._detect_clause_type("甲方应当按时支付款项...")
    assert type_ == "义务"

    # 金额条款
    type_ = splitter._detect_clause_type("合同总金额为人民币100万元...")
    assert type_ == "金额"


def test_split_simple():
    """测试简单分块"""
    splitter = ClauseSplitter()

    content_blocks = [
        {"content": "第一条 总则\n本合同依据相关法律法规制定", "page_number": 1, "type": "text"},
        {"content": "第二条 定义\n以下术语具有如下含义", "page_number": 1, "type": "text"},
        {"content": "本合同中所有条款均具有法律效力", "page_number": 2, "type": "text"},
    ]

    clauses = splitter.split(content_blocks)

    assert len(clauses) >= 2
    assert clauses[0].clause_title == "第一条 总则"
    assert clauses[1].clause_title == "第二条 定义"


def test_to_dict_list():
    """测试转换为字典"""
    splitter = ClauseSplitter()

    clauses = [
        ClauseBlock(
            clause_id="clause_1",
            clause_type="定义",
            clause_title="第一条",
            content="测试内容",
            page_number=1,
            parent_clause_id=None,
            metadata={},
        )
    ]

    dict_list = splitter.to_dict_list(clauses)

    assert len(dict_list) == 1
    assert dict_list[0]["clause_id"] == "clause_1"
    assert dict_list[0]["content"] == "测试内容"