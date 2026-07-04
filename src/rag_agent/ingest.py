"""수집 파이프라인: 문서 로드 → 청킹 → 임베딩 → Chroma 색인.

두 가지 소스를 지원한다.
- 샘플 모드: sample_docs/ 의 마크다운 파일 (Notion 준비 전 파이프라인 검증용)
- Notion 모드: notion_loader 를 통해 실제 Notion DB에서 로드
"""

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_agent import config


def load_sample_docs() -> list[Document]:
    """sample_docs/ 의 마크다운 파일을 Document 리스트로 로드한다."""
    docs = []
    for path in sorted(config.SAMPLE_DOCS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        # 첫 번째 헤딩을 제목으로 사용
        title = next(
            (line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("#")),
            path.stem,
        )
        docs.append(
            Document(
                page_content=text,
                metadata={"title": title, "source": path.name},
            )
        )
    return docs


def split_documents(docs: list[Document]) -> list[Document]:
    """문서를 검색 단위 청크로 분할한다. 원본 메타데이터는 각 청크에 복사된다."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],  # 문단 → 줄 → 단어 순으로 자연스러운 경계 우선
    )
    return splitter.split_documents(docs)


def build_index(docs: list[Document]) -> Chroma:
    """청크를 임베딩하여 Chroma에 저장한다. 기존 색인은 컬렉션 리셋 후 재구축(멱등).

    폴더 삭제(rmtree) 대신 컬렉션 리셋을 쓰는 이유: Windows에서는 Streamlit 등
    다른 프로세스가 Chroma 파일을 열고 있으면 삭제가 파일 잠금으로 실패한다.
    """
    chunks = split_documents(docs)

    vectorstore = Chroma(
        collection_name=config.COLLECTION_NAME,
        embedding_function=OpenAIEmbeddings(model=config.EMBEDDING_MODEL),
        persist_directory=str(config.CHROMA_DIR),
    )
    vectorstore.reset_collection()  # 기존 데이터 비우기
    vectorstore.add_documents(chunks)

    print(f"색인 완료: 문서 {len(docs)}개 → 청크 {len(chunks)}개 → {config.CHROMA_DIR}")
    return vectorstore
