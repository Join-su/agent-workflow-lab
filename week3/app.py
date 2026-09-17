from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from fastapi import FastAPI, HTTPException
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


class ChangeRequest(BaseModel):
    request: str = Field(min_length=5, max_length=500)
    user_role: str = Field(pattern="^(employee|manager)$")


class ChangeState(TypedDict, total=False):
    request: str
    user_role: str
    policy_docs: list[Document]
    retrieval_trace: list[dict[str, str | float | bool]]
    citations: list[dict[str, str]]
    draft: str
    revision_count: int
    revision_requested: bool
    policy_bypass: bool
    status: str
    reason: str | None
    human_review_packet: dict | None
    agents_run: Annotated[list[str], operator.add]


POLICY_DOCUMENT = Document(
    page_content="보안 제어 우회, 정책 예외, 긴급 배포는 자동 승인하지 않고 권한 있는 승인자의 검토와 기록이 필요합니다.",
    metadata={"document_id": "security-policy", "chunk_id": "security-policy-04"},
)
SPLITTER = RecursiveCharacterTextSplitter(chunk_size=120, chunk_overlap=0)
POLICY_CHUNKS = SPLITTER.split_documents([POLICY_DOCUMENT])


def _retrieve_policy_documents(request: str) -> list[Document]:
    if is_live_mode():
        return retrieve_documents(WEEK_COLLECTIONS["week3"], request)
    return POLICY_CHUNKS


policy_retrieval_chain = RunnableLambda(_retrieve_policy_documents)


def planner_node(state: ChangeState) -> ChangeState:
    revision_count = state.get("revision_count", 0)
    if state.get("revision_requested"):
        revision_count += 1
    if is_live_mode():
        documents, retrieval_trace = retrieve_documents_with_trace(
            WEEK_COLLECTIONS["week3"], state["request"]
        )
    else:
        documents = policy_retrieval_chain.invoke(state["request"])
        retrieval_trace = []
    return {
        "policy_docs": documents,
        "citations": citations_for(documents),
        "retrieval_trace": retrieval_trace,
        "draft": (
            generate_grounded_text(
                state["request"],
                documents,
                task="Draft a Korean IT change-review plan grounded in the evidence. Do not execute changes.",
            )
            if is_live_mode() and documents
            else "정책 근거와 권한을 확인한 뒤 변경안을 제시한다."
        ),
        "revision_count": revision_count,
        "agents_run": ["planner"],
    }


def route_after_planner(state: ChangeState) -> Literal[
    "evidence_reviewer", "synthesizer", "insufficient_evidence"
]:
    if not state["policy_docs"]:
        return "insufficient_evidence"
    return "synthesizer" if state.get("revision_requested") else "evidence_reviewer"


def evidence_reviewer_node(state: ChangeState) -> ChangeState:
    policy_bypass = any(
        phrase in state["request"]
        for phrase in ("무시", "우회", "예외", "긴급 배포", "긴급 권한")
    )
    return {
        "policy_bypass": policy_bypass,
        "revision_requested": policy_bypass and state["revision_count"] == 0,
        "agents_run": ["evidence_reviewer"],
    }


def risk_reviewer_node(state: ChangeState) -> ChangeState:
    if state["policy_bypass"]:
        return {
            "reason": "policy_bypass_requested",
            "agents_run": ["risk_reviewer"],
        }
    return {"reason": None, "agents_run": ["risk_reviewer"]}


def route_after_risk(state: ChangeState) -> Literal["planner", "synthesizer"]:
    return "planner" if state.get("revision_requested") else "synthesizer"


def synthesizer_node(state: ChangeState) -> ChangeState:
    if state["policy_bypass"]:
        packet = {
            "request": state["request"],
            "evidence": state["citations"],
            "reason": state["reason"],
            "decision_needed": "승인 권한자가 정책 예외 여부를 판단",
        }
        return {
            "status": "human_review",
            "human_review_packet": packet,
            "agents_run": ["synthesizer"],
        }
    return {
        "status": "done",
        "human_review_packet": None,
        "agents_run": ["synthesizer"],
    }


def insufficient_evidence_node(_: ChangeState) -> ChangeState:
    return {
        "status": "insufficient_evidence",
        "human_review_packet": None,
        "agents_run": ["insufficient_evidence"],
    }


def build_graph():
    graph = StateGraph(ChangeState)
    graph.add_node("planner", planner_node)
    graph.add_node("evidence_reviewer", evidence_reviewer_node)
    graph.add_node("risk_reviewer", risk_reviewer_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("insufficient_evidence", insufficient_evidence_node)
    graph.add_edge(START, "planner")
    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "evidence_reviewer": "evidence_reviewer",
            "synthesizer": "synthesizer",
            "insufficient_evidence": "insufficient_evidence",
        },
    )
    graph.add_edge("evidence_reviewer", "risk_reviewer")
    graph.add_conditional_edges(
        "risk_reviewer",
        route_after_risk,
        {"planner": "planner", "synthesizer": "synthesizer"},
    )
    graph.add_edge("synthesizer", END)
    graph.add_edge("insufficient_evidence", END)
    return graph.compile()


WORKFLOW = build_graph()


def run_change_review(payload: ChangeRequest) -> dict:
    state = WORKFLOW.invoke({**payload.model_dump(), "revision_count": 0, "agents_run": []})
    return {
        "difficulty": 3,
        "mode": "live" if is_live_mode() else "fixture",
        "business_use_case": "it_change_risk_review",
        "workflow_engine": "langgraph",
        "agents_run": state["agents_run"],
        "revision_count": state["revision_count"],
        "status": state["status"],
        "citations": state["citations"],
        "retrieval_trace": state.get("retrieval_trace", []),
        "human_review_packet": state["human_review_packet"],
        "draft": state["draft"],
    }


def create_app() -> FastAPI:
    app = FastAPI(title="Week 3 — LangGraph Change Review", version="2.0.0")

    @app.get("/health")
    def health() -> dict[str, str | int | bool]:
        return {
            "status": "ok",
            "difficulty": 3,
            "workflow_engine": "langgraph",
            "live_mode": is_live_mode(),
        }

    @app.get("/diagnostics")
    def diagnostics(include_chunks: bool = False) -> dict:
        try:
            return collection_diagnostics(
                WEEK_COLLECTIONS["week3"], include_chunks=include_chunks
            )
        except LiveRagError as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "live_rag_unavailable", "message": str(error)},
            ) from error

    @app.post("/review-change")
    def review_change(payload: ChangeRequest) -> dict:
        try:
            return run_change_review(payload)
        except LiveRagError as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "live_rag_unavailable", "message": str(error)},
            ) from error

    return app


app = create_app()
