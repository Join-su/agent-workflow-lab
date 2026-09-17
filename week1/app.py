from __future__ import annotations

import operator
from dataclasses import dataclass
from typing import Annotated, Callable, Literal, Protocol, TypedDict

from fastapi import FastAPI, HTTPException, Response
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from shared.live_rag import (
    WEEK_COLLECTIONS,
    LiveRagError,
    citations_for,
    generate_grounded_text,
    is_live_mode,
    retrieve_documents,
)


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=300)


@dataclass
class PolicyServices:
    retriever: Retriever
    answer: Callable[[str, list[Document]], str]
    mode: Literal["fixture", "live"]


class QueryState(TypedDict, total=False):
    question: str
    documents: list[Document]
    answer: str | None
    status: str
    citations: list[dict[str, str]]
    steps: Annotated[list[str], operator.add]


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
    return {
        "retrieved_docs": retrieval_chain.invoke(state["question"]),
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
            "status": "answered" if documents else "insufficient_evidence",
            "citations": citations(documents),
            "steps": ["grounding_guard"],
        }

    graph = StateGraph(QueryState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("answer", answer)
    graph.add_node("grounding_guard", guard)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", "grounding_guard")
    graph.add_edge("grounding_guard", END)
    return graph.compile()


def run_policy_query(question: str, services: PolicyServices | None = None) -> dict:
    services = services or create_fixture_services()
    state = build_workflow(services).invoke({"question": question, "steps": []})
    return {
        "difficulty": 1,
        "business_use_case": "hr_policy_qa",
        "mode": services.mode,
        "status": state["status"],
        "answer": state["answer"],
        "citations": state["citations"],
        "steps": state["steps"],
    }


def create_app(services: PolicyServices | None = None, *, mode: str | None = None) -> FastAPI:
    selected_mode = resolve_mode(mode)
    if services is None:
        services = create_live_services() if selected_mode == "live" else create_fixture_services()
    api = FastAPI(title="Week 1 — Grounded HR Policy Q&A", version="3.0.0")

    @app.get("/")
    def root() -> dict[str, str]:
        """Provide a browser-friendly entry point for the API service."""
        return {
            "message": "Week 1 policy Q&A API is running.",
            "health": "/health",
            "query": "POST /query",
            "docs": "/docs",
        }

    @app.get("/favicon.ico", include_in_schema=False, status_code=204)
    def favicon() -> Response:
        """Avoid a noisy 404 when a browser requests the optional site icon."""
        return Response(status_code=204)

    @app.get("/health")
    def health() -> dict[str, str | int | bool]:
        return {
            "status": "ok",
            "difficulty": 1,
            "workflow_engine": "langgraph",
            "live_mode": is_live_mode(),
        }

    @api.post("/query")
    def query(payload: QueryRequest) -> dict:
        try:
            return run_query(payload.question)
        except LiveRagError as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "live_rag_unavailable", "message": str(error)},
            ) from error

    return api


app = create_app()
