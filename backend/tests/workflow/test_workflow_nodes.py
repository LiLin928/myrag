# backend/tests/workflow/test_workflow_nodes.py

import pytest
from app.workflow.nodes.base_node import BaseNode, NodeResult
from app.workflow.nodes.llm_node import LLMNode
from app.workflow.nodes.rag_node import RAGNode
from app.workflow.nodes.code_node import CodeNode
from app.workflow.nodes.http_node import HTTPNode
from app.workflow.nodes.condition_node import ConditionNode
from app.workflow.nodes.human_node import HumanNode
from app.workflow.nodes.start_node import StartNode
from app.workflow.nodes.end_node import EndNode
from app.workflow.nodes.loop_node import LoopNode
from app.workflow.nodes.tool_node import ToolNode


def test_node_result():
    """测试节点结果"""
    result = NodeResult(
        success=True,
        output={"key": "value"},
        error=None,
        next_node="next",
    )

    assert result.success is True
    assert result.output == {"key": "value"}
    assert result.next_node == "next"

    result_dict = result.to_dict()
    assert result_dict["success"] is True


def test_llm_node_init():
    """测试 LLM 节点初始化"""
    node = LLMNode(
        node_id="llm_1",
        config={
            "model": "gpt-4o-mini",
            "user_prompt": "Hello",
        }
    )

    assert node.node_id == "llm_1"
    assert node.node_type == "llm"
    assert node.config["model"] == "gpt-4o-mini"


def test_rag_node_init():
    """测试 RAG 节点初始化"""
    node = RAGNode(
        node_id="rag_1",
        config={
            "project_id": 1,
            "top_k": 5,
            "query": "search query",
        }
    )

    assert node.node_id == "rag_1"
    assert node.node_type == "rag"


def test_code_node_init():
    """测试 Code 节点初始化"""
    node = CodeNode(
        node_id="code_1",
        config={
            "code": "print('hello')",
            "timeout": 30,
        }
    )

    assert node.node_id == "code_1"
    assert node.node_type == "code"


def test_http_node_init():
    """测试 HTTP 节点初始化"""
    node = HTTPNode(
        node_id="http_1",
        config={
            "url": "https://example.com",
            "method": "GET",
        }
    )

    assert node.node_id == "http_1"
    assert node.node_type == "http"


def test_condition_node_init():
    """测试条件节点初始化"""
    node = ConditionNode(
        node_id="cond_1",
        config={
            "expression": "{{score}} > 0.5",
            "branches": {"true": "node_a", "false": "node_b"},
        }
    )

    assert node.node_id == "cond_1"
    assert node.node_type == "condition"


def test_human_node_init():
    """测试人工节点初始化"""
    node = HumanNode(
        node_id="human_1",
        config={
            "prompt": "请输入：",
        }
    )

    assert node.node_id == "human_1"
    assert node.node_type == "human"


def test_start_node_init():
    """测试开始节点初始化"""
    node = StartNode(
        node_id="start",
        config={"variables": {"initial": "value"}}
    )

    assert node.node_type == "start"


def test_end_node_init():
    """测试结束节点初始化"""
    node = EndNode(node_id="end", config={})

    assert node.node_type == "end"


def test_loop_node_init():
    """测试循环节点初始化"""
    node = LoopNode(
        node_id="loop_1",
        config={"items_key": "items", "loop_var": "item"}
    )

    assert node.node_type == "loop"


def test_tool_node_init():
    """测试工具节点初始化"""
    node = ToolNode(
        node_id="tool_1",
        config={"tool_name": "knowledge_search"}
    )

    assert node.node_type == "tool"


def test_base_node_render_template():
    """测试模板渲染"""
    node = LLMNode(node_id="test", config={})

    template = "Hello {{name}}, today is {{day}}"
    state = {"variables": {"name": "Alice", "day": "Monday"}}

    rendered = node.render_template(template, state)

    assert rendered == "Hello Alice, today is Monday"


def test_get_supported_node_types():
    """测试获取支持的节点类型"""
    from app.workflow.engine import get_supported_node_types

    types = get_supported_node_types()

    assert "start" in types
    assert "end" in types
    assert "llm" in types
    assert "rag" in types
    assert "code" in types
    assert "http" in types
    assert "condition" in types
    assert "human" in types