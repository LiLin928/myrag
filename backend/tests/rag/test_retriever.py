# backend/tests/rag/test_retriever.py

import pytest
from app.rag.retrieval.pgvector_retriever import PGVectorRetriever


def test_retriever_init():
    """测试检索器初始化"""
    retriever = PGVectorRetriever(project_id=1)

    assert retriever.project_id == 1
    assert retriever.top_k == 5
    assert retriever.score_threshold == 0.0


def test_retriever_custom_params():
    """测试自定义参数"""
    retriever = PGVectorRetriever(
        project_id=2,
        top_k=10,
        score_threshold=0.5,
        dimension=768,
    )

    assert retriever.project_id == 2
    assert retriever.top_k == 10
    assert retriever.score_threshold == 0.5
    assert retriever.dimension == 768


def test_retriever_no_project():
    """测试无项目 ID"""
    retriever = PGVectorRetriever()

    assert retriever.project_id is None
    assert retriever.top_k == 5