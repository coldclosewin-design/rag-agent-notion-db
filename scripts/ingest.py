"""색인 구축 CLI.

사용법:
    python scripts/ingest.py --sample   # sample_docs/ 로 색인 (Notion 불필요)
    python scripts/ingest.py            # 실제 Notion DB에서 수집하여 색인
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_agent.ingest import build_index, load_sample_docs  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Notion RAG 색인 구축")
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Notion 대신 sample_docs/ 마크다운으로 색인 (오프라인 테스트용)",
    )
    args = parser.parse_args()

    if args.sample:
        docs = load_sample_docs()
    else:
        from rag_agent.notion_loader import load_notion_database

        docs = load_notion_database()

    if not docs:
        print("로드된 문서가 없습니다. 소스를 확인하세요.")
        sys.exit(1)

    vectorstore = build_index(docs)

    # 스모크 체크: 색인이 실제로 검색 가능한지 확인
    results = vectorstore.similarity_search("RAG가 무엇인가요?", k=2)
    print("\n[검증] 유사도 검색 상위 결과:")
    for doc in results:
        print(f"  - {doc.metadata.get('title', '?')}: {doc.page_content[:60]!r}...")


if __name__ == "__main__":
    main()
