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


class ExpenseRequest(BaseModel):
    amount: int = Field(gt=0, le=1_000_000)
    receipt_attached: bool
    purpose: str = Field(min_length=3, max_length=80)


class ExpenseState(TypedDict, total=False):
    amount: int
    receipt_attached: bool
    purpose: str
    policy_docs: list[Document]
    retrieval_trace: list[dict[str, str | float | bool]]
    missing: list[str]
    citations: list[dict[str, str]]
    required_follow_up: str | None
    route: Literal["clarify", "next_step", "insufficient_evidence"]
    status: str
    review_summary: str | None
    agents_run: Annotated[list[str], operator.add]


POLICY_DOCUMENT = Document(
    page_content="출장비 사전 검토에는 영수증과 업무 목적이 필요하며, 영수증이 없으면 receipt_required 보완 요청으로 처리합니다.",
    metadata={"document_id": "expense-policy", "chunk_id": "expense-policy-02"},
)
SPLITTER = RecursiveCharacterTextSplitter(chunk_size=120, chunk_overlap=0)
POLICY_CHUNKS = SPLITTER.split_documents([POLICY_DOCUMENT])


def _retrieve_policy_documents(purpose: str) -> list[Document]:
    if is_live_mode():
        return retrieve_documents(WEEK_COLLECTIONS["week2"], purpose)
    return POLICY_CHUNKS


policy_retrieval_chain = RunnableLambda(_retrieve_policy_documents)


def policy_retriever_node(state: ExpenseState) -> ExpenseState:
    if is_live_mode():
        documents, retrieval_trace = retrieve_documents_with_trace(
            WEEK_COLLECTIONS["week2"], state["purpose"]
        )
    else:
        documents = policy_retrieval_chain.invoke(state["purpose"])
        retrieval_trace = []
    return {
        "policy_docs": documents,
        "citations": citations_for(documents),
        "retrieval_trace": retrieval_trace,
        "agents_run": ["policy_retriever"],
    }


def evidence_extractor_node(state: ExpenseState) -> ExpenseState:
    missing = [] if state["receipt_attached"] else ["receipt_required"]
    return {"missing": missing, "agents_run": ["evidence_extractor"]}


def policy_reviewer_node(state: ExpenseState) -> ExpenseState:
    summary = None
    if is_live_mode() and state["policy_docs"]:
        summary = generate_grounded_text(
            state["purpose"],
            state["policy_docs"],
            task="Summarize the applicable expense-policy evidence in Korean. Do not approve payment.",
        )
    return {"review_summary": summary, "agents_run": ["policy_reviewer"]}


def risk_router_node(state: ExpenseState) -> ExpenseState:
    if not state["policy_docs"]:
        return {
            "route": "insufficient_evidence",
            "required_follow_up": None,
            "agents_run": ["risk_router"],
        }
    if state["missing"]:
        return {
            "route": "clarify",
            "required_follow_up": state["missing"][0],
            "agents_run": ["risk_router"],
        }
    return {
        "route": "next_step",
        "required_follow_up": None,
        "agents_run": ["risk_router"],
    }


def route_after_review(state: ExpenseState) -> Literal[
    "clarify", "next_step", "insufficient_evidence"
]:
    return state["route"]


def clarify_node(_: ExpenseState) -> ExpenseState:
    return {"status": "clarify"}


def next_step_node(_: ExpenseState) -> ExpenseState:
    return {"status": "approved_for_next_step"}


def insufficient_evidence_node(_: ExpenseState) -> ExpenseState:
    return {"status": "insufficient_evidence"}


def build_graph():
    graph = StateGraph(ExpenseState)
    graph.add_node("policy_retriever", policy_retriever_node)
    graph.add_node("evidence_extractor", evidence_extractor_node)
    graph.add_node("policy_reviewer", policy_reviewer_node)
    graph.add_node("risk_router", risk_router_node)
    graph.add_node("clarify", clarify_node)
    graph.add_node("next_step", next_step_node)
    graph.add_node("insufficient_evidence", insufficient_evidence_node)
    graph.add_edge(START, "policy_retriever")
    graph.add_edge("policy_retriever", "evidence_extractor")
    graph.add_edge("evidence_extractor", "policy_reviewer")
    graph.add_edge("policy_reviewer", "risk_router")
    graph.add_conditional_edges(
        "risk_router",
        route_after_review,
        {
            "clarify": "clarify",
            "next_step": "next_step",
            "insufficient_evidence": "insufficient_evidence",
        },
    )
    graph.add_edge("clarify", END)
    graph.add_edge("next_step", END)
    graph.add_edge("insufficient_evidence", END)
    return graph.compile()


WORKFLOW = build_graph()


def run_expense_review(payload: ExpenseRequest) -> dict:
    state = WORKFLOW.invoke({**payload.model_dump(), "agents_run": []})
    return {
        "difficulty": 2,
        "mode": "live" if is_live_mode() else "fixture",
        "business_use_case": "expense_claim_precheck",
        "workflow_engine": "langgraph",
        "agents_run": state["agents_run"],
        "status": state["status"],
        "required_follow_up": state["required_follow_up"],
        "citations": state["citations"],
        "retrieval_trace": state.get("retrieval_trace", []),
        "review_summary": state.get("review_summary"),
    }


def create_app() -> FastAPI:
    app = FastAPI(title="Week 2 — LangChain Expense Review", version="2.0.0")

    @app.get("/health")
    def health() -> dict[str, str | int | bool]:
        return {
            "status": "ok",
            "difficulty": 2,
            "workflow_engine": "langgraph",
            "live_mode": is_live_mode(),
        }

    @app.get("/diagnostics")
    def diagnostics(include_chunks: bool = False) -> dict:
        try:
            return collection_diagnostics(
                WEEK_COLLECTIONS["week2"], include_chunks=include_chunks
            )
        except LiveRagError as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "live_rag_unavailable", "message": str(error)},
            ) from error

    @app.post("/review")
    def review(payload: ExpenseRequest) -> dict:
        try:
            return run_expense_review(payload)
        except LiveRagError as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "live_rag_unavailable", "message": str(error)},
            ) from error

    return app


app = create_app()
