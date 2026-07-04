"""Streamlit 채팅 UI.

실행: streamlit run app.py
사전 조건: 색인이 구축되어 있어야 한다 (python scripts/ingest.py --sample 또는 Notion 모드).
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from rag_agent import config  # noqa: E402
from rag_agent.graph import build_graph  # noqa: E402

st.set_page_config(page_title="Notion RAG Agent", page_icon="📚")


@st.cache_resource
def get_graph():
    """그래프는 한 번만 compile하여 재사용한다."""
    return build_graph()


# --- 사이드바: 색인 상태 ---
with st.sidebar:
    st.header("📚 Notion RAG Agent")
    st.caption("LangGraph self-corrective RAG 스터디 프로젝트")

    if config.CHROMA_DIR.exists():
        st.success("벡터 색인 준비됨")
    else:
        st.error(
            "벡터 색인이 없습니다.\n\n"
            "터미널에서 먼저 실행하세요:\n"
            "`python scripts/ingest.py --sample`"
        )

    st.divider()
    st.markdown(f"**LLM**: `{config.OPENAI_MODEL}`")
    st.markdown(f"**임베딩**: `{config.EMBEDDING_MODEL}`")
    st.markdown(f"**Top-K**: {config.RETRIEVAL_TOP_K}")

    if st.button("대화 초기화"):
        st.session_state.messages = []
        st.rerun()

# --- 채팅 히스토리 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("🔍 참고한 문서 (검색 결과)"):
                for src in msg["sources"]:
                    st.markdown(f"**{src['title']}**")
                    st.caption(src["preview"])

# --- 입력 처리 ---
if question := st.chat_input("Notion 문서에 대해 질문해 보세요"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("검색하고 답변을 생성하는 중..."):
            result = get_graph().invoke(
                {
                    "question": question,
                    "query": "",
                    "documents": [],
                    "generation": "",
                    "retry_count": 0,
                }
            )

        st.markdown(result["generation"])

        sources = [
            {
                "title": doc.metadata.get("title", "제목 없음"),
                "preview": doc.page_content[:200] + "...",
            }
            for doc in result["documents"]
        ]
        if sources:
            with st.expander("🔍 참고한 문서 (검색 결과)"):
                for src in sources:
                    st.markdown(f"**{src['title']}**")
                    st.caption(src["preview"])
        if result["retry_count"] > 0:
            st.caption(f"💡 쿼리 재작성 {result['retry_count']}회 수행됨 (최종 쿼리: {result['query']})")

    st.session_state.messages.append(
        {"role": "assistant", "content": result["generation"], "sources": sources}
    )
