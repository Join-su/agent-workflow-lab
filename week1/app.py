from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from fastapi import FastAPI, HTTPException, Response
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from shared.live_rag import (
    WEEK_COLLECTIONS,
    LiveRagError,
    citations_for,
    collection_diagnostics,
    generate_grounded_text,
    is_live_mode,
    retrieve_documents_with_trace,
)


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=300)


class QueryState(TypedDict, total=False):
    question: str
    retrieved_docs: list[Document]
    retrieval_trace: list[dict[str, str | float | bool]]
    answer: str | None
    citations: list[dict[str, str]]
    status: str
    reason: str | None
    agents_run: Annotated[list[str], operator.add]


SOURCE_DOCUMENT = Document(
    page_content="휴가 신청은 시작일 기준 영업일 3일 전까지 하며, 인수인계 대상을 입력해야 합니다.",
    metadata={"document_id": "leave-policy", "chunk_id": "leave-policy-01"},
)
SPLITTER = RecursiveCharacterTextSplitter(chunk_size=120, chunk_overlap=0)
POLICY_CHUNKS = SPLITTER.split_documents([SOURCE_DOCUMENT])


def _retrieve_documents(question: str) -> list[Document]:
    if is_live_mode():
        return retrieve_documents(WEEK_COLLECTIONS["week1"], question)
    tokens = set(question.replace("?", "").split())
    return [
        document
        for document in POLICY_CHUNKS
        if tokens & set(document.page_content.replace(".", "").split())
    ]


retrieval_chain = RunnableLambda(_retrieve_documents)


def retrieve_node(state: QueryState) -> QueryState:
    if is_live_mode():
        documents, retrieval_trace = retrieve_documents_with_trace(
            WEEK_COLLECTIONS["week1"], state["question"]
        )
    else:
        documents = retrieval_chain.invoke(state["question"])
        retrieval_trace = []
    return {
        "retrieved_docs": documents,
        "retrieval_trace": retrieval_trace,
        "agents_run": ["retriever"],
    }


def answer_node(state: QueryState) -> QueryState:
    evidence = state["retrieved_docs"]
    if not evidence:
        return {"answer": None, "citations": [], "agents_run": ["answer"]}

    document = evidence[0]
    answer = (
        generate_grounded_text(
            state["question"],
            evidence,
            task="Answer the employee's HR policy question concisely in Korean.",
        )
        if is_live_mode()
        else document.page_content
    )
    return {
        "answer": answer,
        "citations": citations_for(evidence),
        "agents_run": ["answer"],
    }


def evidence_guard_node(state: QueryState) -> QueryState:
    if state["retrieved_docs"]:
        return {
            "status": "answered",
            "reason": None,
            "agents_run": ["evidence_guard"],
        }
    return {
        "status": "insufficient_evidence",
        "reason": "no_matching_policy",
        "agents_run": ["evidence_guard"],
    }


def build_graph():
    graph = StateGraph(QueryState)
    graph.add_node("retriever", retrieve_node)
    graph.add_node("answer", answer_node)
    graph.add_node("evidence_guard", evidence_guard_node)
    graph.add_edge(START, "retriever")
    graph.add_edge("retriever", "answer")
    graph.add_edge("answer", "evidence_guard")
    graph.add_edge("evidence_guard", END)
    return graph.compile()


WORKFLOW = build_graph()


def run_query(question: str) -> dict:
    state = WORKFLOW.invoke({"question": question, "agents_run": []})
    return {
        "difficulty": 1,
        "mode": "live" if is_live_mode() else "fixture",
        "business_use_case": "hr_leave_policy_self_service",
        "workflow_engine": "langgraph",
        "agents_run": state["agents_run"],
        "status": state["status"],
        "answer": state["answer"],
        "citations": state["citations"],
        "retrieval_trace": state.get("retrieval_trace", []),
        "reason": state["reason"],
    }


def create_app() -> FastAPI:
    app = FastAPI(title="Week 1 — LangChain Policy Q&A", version="2.0.0")

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "message": "Week 1 policy Q&A API is running.",
            "health": "/health",
            "query": "POST /query",
            "docs": "/docs",
        }

    @app.get("/favicon.ico", include_in_schema=False, status_code=204)
    def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/health")
    def health() -> dict[str, str | int | bool]:
        return {
            "status": "ok",
            "difficulty": 1,
            "workflow_engine": "langgraph",
            "live_mode": is_live_mode(),
        }

    @app.get("/diagnostics")
    def diagnostics(include_chunks: bool = False) -> dict:
        try:
            return collection_diagnostics(
                WEEK_COLLECTIONS["week1"], include_chunks=include_chunks
            )
        except LiveRagError as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "live_rag_unavailable", "message": str(error)},
            ) from error

    @app.post("/query")
    def query(payload: QueryRequest) -> dict:
        try:
            return run_query(payload.question)
        except LiveRagError as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "live_rag_unavailable", "message": str(error)},
            ) from error

    return app


app = create_app()
