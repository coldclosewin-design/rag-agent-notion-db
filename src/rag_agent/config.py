"""프로젝트 전역 설정.

모든 조정 가능한 값(모델, 청크 크기, 경로)을 한 곳에 모아 실험을 쉽게 한다.
.env 파일은 프로젝트 루트에 두며, import 시점에 자동 로드된다.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 프로젝트 루트 = src/rag_agent/config.py 의 두 단계 위
PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

# --- LLM / 임베딩 ---
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = "text-embedding-3-small"

# --- Notion ---
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
# 쉼표로 구분하여 여러 데이터베이스 지정 가능 (예: "id1,id2,id3")
NOTION_DATABASE_IDS = [
    db_id.strip()
    for db_id in os.getenv("NOTION_DATABASE_ID", "").split(",")
    if db_id.strip()
]

# --- 벡터 스토어 ---
CHROMA_DIR = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "notion_docs"

# --- 청킹 ---
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# --- 검색 ---
RETRIEVAL_TOP_K = 4

# --- 그래프 ---
MAX_QUERY_REWRITES = 2  # 쿼리 재작성 최대 횟수 (무한 루프 방지)

# --- 샘플 문서 (Notion 없이 테스트용) ---
SAMPLE_DOCS_DIR = PROJECT_ROOT / "sample_docs"
