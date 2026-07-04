"""API 호출 없이 검증 가능한 부분의 스모크 테스트.

실행: python -m pytest tests/ -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from langchain_core.documents import Document

from rag_agent.ingest import load_sample_docs, split_documents


def test_load_sample_docs():
    docs = load_sample_docs()
    assert len(docs) >= 3
    for doc in docs:
        assert doc.page_content
        assert doc.metadata["title"]
        assert doc.metadata["source"].endswith(".md")


def test_split_documents_preserves_metadata():
    docs = [
        Document(
            page_content="문단 하나.\n\n" + ("긴 내용 " * 300),
            metadata={"title": "테스트", "source": "test.md"},
        )
    ]
    chunks = split_documents(docs)
    assert len(chunks) > 1  # 긴 문서는 여러 청크로 분할
    for chunk in chunks:
        assert chunk.metadata["title"] == "테스트"


def test_graph_structure():
    """그래프가 compile되고 설계한 노드/엣지를 가지는지 확인 (LLM 호출 없음)."""
    from rag_agent.graph import build_graph

    graph = build_graph()
    nodes = set(graph.get_graph().nodes)
    assert {"retrieve", "grade_documents", "rewrite_query", "generate"} <= nodes

    edges = {(e.source, e.target) for e in graph.get_graph().edges}
    assert ("retrieve", "grade_documents") in edges
    assert ("rewrite_query", "retrieve") in edges  # 재시도 루프


def test_notion_block_to_markdown():
    from rag_agent.notion_loader import _block_to_markdown

    block = {
        "type": "heading_2",
        "heading_2": {"rich_text": [{"plain_text": "제목입니다"}]},
    }
    assert _block_to_markdown(block) == "## 제목입니다"

    code_block = {
        "type": "code",
        "code": {"rich_text": [{"plain_text": "print('hi')"}], "language": "python"},
    }
    assert _block_to_markdown(code_block) == "```python\nprint('hi')\n```"
