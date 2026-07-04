"""저장된 Chroma 색인을 로드하여 retriever를 생성한다."""

from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_openai import OpenAIEmbeddings

from rag_agent import config


def get_vectorstore() -> Chroma:
    if not config.CHROMA_DIR.exists():
        raise FileNotFoundError(
            f"벡터 스토어가 없습니다: {config.CHROMA_DIR}\n"
            "먼저 색인을 만드세요: python scripts/ingest.py --sample (또는 Notion 모드)"
        )
    return Chroma(
        collection_name=config.COLLECTION_NAME,
        embedding_function=OpenAIEmbeddings(model=config.EMBEDDING_MODEL),
        persist_directory=str(config.CHROMA_DIR),
    )


def get_retriever(k: int = config.RETRIEVAL_TOP_K) -> VectorStoreRetriever:
    return get_vectorstore().as_retriever(search_kwargs={"k": k})
