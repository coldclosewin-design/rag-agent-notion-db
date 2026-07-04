"""LangGraph가 자동 생성하는 Mermaid 다이어그램을 docs/images/ 에 저장한다.

사용법: python scripts/draw_graph.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_agent.graph import build_graph  # noqa: E402

OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "images" / "graph.mmd"


def main() -> None:
    graph = build_graph()
    mermaid = graph.get_graph().draw_mermaid()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(mermaid, encoding="utf-8")
    print(f"Mermaid 다이어그램 저장: {OUTPUT}")
    print("\n" + mermaid)


if __name__ == "__main__":
    main()
