"""节点路由器

根据节点类型创建对应的节点处理器
"""

from typing import Dict, Any, Type
from app.workflow.nodes.base_node import BaseNode
from app.workflow.nodes import (
    LLMNode,
    RAGNode,
    CodeNode,
    HTTPNode,
    ConditionNode,
    LoopNode,
    HumanNode,
    StartNode,
    EndNode,
    ToolNode,
)


NODE_TYPE_MAP: Dict[str, Type[BaseNode]] = {
    "start": StartNode,
    "end": EndNode,
    "llm": LLMNode,
    "rag": RAGNode,
    "code": CodeNode,
    "http": HTTPNode,
    "condition": ConditionNode,
    "loop": LoopNode,
    "human": HumanNode,
    "tool": ToolNode,
}


def create_node(node_id: str, node_type: str, config: Dict[str, Any]) -> BaseNode:
    """创建节点实例

    Args:
        node_id: 节点 ID
        node_type: 节点类型
        config: 节点配置

    Returns:
        节点实例
    """
    node_class = NODE_TYPE_MAP.get(node_type)
    if not node_class:
        raise ValueError(f"Unknown node type: {node_type}")

    return node_class(node_id=node_id, config=config)


def get_supported_node_types() -> list:
    """获取支持的节点类型列表"""
    return list(NODE_TYPE_MAP.keys())