"""LangGraph self-corrective RAG 그래프 정의.

흐름:
    START → retrieve → grade_documents ─(관련 문서 있음)────────→ generate → END
                            │
                            ├─(관련 문서 없음, 재시도 가능)→ rewrite_query → retrieve
                            └─(재시도 소진)──────────────────────→ generate
"""

from typing import Literal, TypedDict

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from rag_agent import config, prompts
from rag_agent.retriever import get_retriever


class GraphState(TypedDict):
    """그래프 전체가 공유하는 상태. 각 노드는 변경할 필드만 반환한다."""

    question: str        # 사용자의 원래 질문 (불변)
    query: str           # 현재 검색에 사용하는 쿼리 (rewrite 시 갱신)
    documents: list[Document]  # 관련성 평가를 통과한 검색 결과
    generation: str      # 최종 답변
    retry_count: int     # 쿼리 재작성 횟수


class RelevanceGrade(BaseModel):
    """문서 관련성 평가 결과 (structured output 스키마)."""

    binary_score: Literal["yes", "no"] = Field(
        description="문서가 질문과 관련 있으면 'yes', 없으면 'no'"
    )


def _llm() -> ChatOpenAI:
    return ChatOpenAI(model=config.OPENAI_MODEL, temperature=0)


# --- 노드 ---

def retrieve(state: GraphState) -> dict:
    """현재 쿼리로 벡터 스토어에서 top-k 문서를 검색한다."""
    query = state.get("query") or state["question"]
    documents = get_retriever().invoke(query)
    return {"query": query, "documents": documents}


def grade_documents(state: GraphState) -> dict:
    """LLM으로 각 문서의 질문 관련성을 평가하여 관련 문서만 남긴다."""
    grader = _llm().with_structured_output(RelevanceGrade)
    relevant = []
    for doc in state["documents"]:
        grade = grader.invoke(
            [
                ("system", prompts.GRADE_SYSTEM),
                ("user", prompts.GRADE_USER.format(
                    document=doc.page_content, question=state["question"]
                )),
            ]
        )
        if grade.binary_score == "yes":
            relevant.append(doc)
    return {"documents": relevant}


def rewrite_query(state: GraphState) -> dict:
    """검색이 부실할 때 검색용 쿼리를 재작성한다."""
    response = _llm().invoke(
        [
            ("system", prompts.REWRITE_SYSTEM),
            ("user", prompts.REWRITE_USER.format(
                question=state["question"], query=state["query"]
            )),
        ]
    )
    return {"query": response.content.strip(), "retry_count": state["retry_count"] + 1}


def generate(state: GraphState) -> dict:
    """관련 문서를 컨텍스트로 답변을 생성한다. 문서가 없으면 안내 문구를 반환한다."""
    if not state["documents"]:
        return {"generation": prompts.NO_CONTEXT_ANSWER}

    context = "\n\n---\n\n".join(
        f"[{doc.metadata.get('title', '제목 없음')}]\n{doc.page_content}"
        for doc in state["documents"]
    )
    response = _llm().invoke(
        [
            ("system", prompts.GENERATE_SYSTEM),
            ("user", prompts.GENERATE_USER.format(
                context=context, question=state["question"]
            )),
        ]
    )
    return {"generation": response.content}


# --- 조건부 엣지 ---

def decide_after_grading(state: GraphState) -> Literal["generate", "rewrite_query"]:
    """평가 결과에 따라 다음 노드를 결정한다.

    - 관련 문서가 있으면 → 답변 생성
    - 없고 재시도 여유가 있으면 → 쿼리 재작성 후 재검색
    - 재시도를 소진했으면 → generate (컨텍스트 부족 안내)
    """
    if state["documents"]:
        return "generate"
    if state["retry_count"] < config.MAX_QUERY_REWRITES:
        return "rewrite_query"
    return "generate"


# --- 그래프 조립 ---

def build_graph():
    builder = StateGraph(GraphState)

    builder.add_node("retrieve", retrieve)
    builder.add_node("grade_documents", grade_documents)
    builder.add_node("rewrite_query", rewrite_query)
    builder.add_node("generate", generate)

    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "grade_documents")
    builder.add_conditional_edges("grade_documents", decide_after_grading)
    builder.add_edge("rewrite_query", "retrieve")
    builder.add_edge("generate", END)

    return builder.compile()


def ask(question: str) -> dict:
    """질문 한 건을 그래프에 넣어 최종 상태를 반환하는 편의 함수."""
    graph = build_graph()
    return graph.invoke(
        {"question": question, "query": "", "documents": [], "generation": "", "retry_count": 0}
    )
