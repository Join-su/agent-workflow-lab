from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from fastapi import FastAPI
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


class ExpenseRequest(BaseModel):
    amount: int = Field(gt=0, le=1_000_000)
    receipt_attached: bool
    purpose: str = Field(min_length=3, max_length=80)


class ExpenseState(TypedDict, total=False):
    amount: int
    receipt_attached: bool
    purpose: str
    policy_docs: list[Document]
    missing: list[str]
    citations: list[dict[str, str]]
    required_follow_up: str | None
    route: Literal["clarify", "next_step"]
    status: str
    agents_run: Annotated[list[str], operator.add]


POLICY_DOCUMENT = Document(
    page_content="출장비 정산에는 영수증과 업무 목적이 필요하며, 영수증이 없으면 보완 요청으로 처리합니다.",
    metadata={"document_id": "expense-policy", "chunk_id": "expense-policy-02"},
)
SPLITTER = RecursiveCharacterTextSplitter(chunk_size=120, chunk_overlap=0)
POLICY_CHUNKS = SPLITTER.split_documents([POLICY_DOCUMENT])
policy_retrieval_chain = RunnableLambda(lambda _: POLICY_CHUNKS)


def policy_retriever_node(state: ExpenseState) -> ExpenseState:
    documents = policy_retrieval_chain.invoke(state["purpose"])
    return {
        "policy_docs": documents,
        "citations": [
            {
                "document_id": str(document.metadata["document_id"]),
                "chunk_id": str(document.metadata["chunk_id"]),
            }
            for document in documents
        ],
        "agents_run": ["policy_retriever"],
    }


def evidence_extractor_node(state: ExpenseState) -> ExpenseState:
    missing = [] if state["receipt_attached"] else ["receipt_required"]
    return {"missing": missing, "agents_run": ["evidence_extractor"]}


def policy_reviewer_node(state: ExpenseState) -> ExpenseState:
    return {"agents_run": ["policy_reviewer"]}


def risk_router_node(state: ExpenseState) -> ExpenseState:
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


def route_after_review(state: ExpenseState) -> Literal["clarify", "next_step"]:
    return state["route"]


def clarify_node(_: ExpenseState) -> ExpenseState:
    return {"status": "clarify"}


def next_step_node(_: ExpenseState) -> ExpenseState:
    return {"status": "approved_for_next_step"}


def build_graph():
    graph = StateGraph(ExpenseState)
    graph.add_node("policy_retriever", policy_retriever_node)
    graph.add_node("evidence_extractor", evidence_extractor_node)
    graph.add_node("policy_reviewer", policy_reviewer_node)
    graph.add_node("risk_router", risk_router_node)
    graph.add_node("clarify", clarify_node)
    graph.add_node("next_step", next_step_node)
    graph.add_edge(START, "policy_retriever")
    graph.add_edge("policy_retriever", "evidence_extractor")
    graph.add_edge("evidence_extractor", "policy_reviewer")
    graph.add_edge("policy_reviewer", "risk_router")
    graph.add_conditional_edges(
        "risk_router",
        route_after_review,
        {"clarify": "clarify", "next_step": "next_step"},
    )
    graph.add_edge("clarify", END)
    graph.add_edge("next_step", END)
    return graph.compile()


WORKFLOW = build_graph()


def run_expense_review(payload: ExpenseRequest) -> dict:
    state = WORKFLOW.invoke({**payload.model_dump(), "agents_run": []})
    return {
        "difficulty": 2,
        "business_use_case": "expense_claim_precheck",
        "workflow_engine": "langgraph",
        "agents_run": state["agents_run"],
        "status": state["status"],
        "required_follow_up": state["required_follow_up"],
        "citations": state["citations"],
    }


def create_app() -> FastAPI:
    app = FastAPI(title="Week 2 — LangChain Expense Review", version="2.0.0")

    @app.get("/health")
    def health() -> dict[str, str | int]:
        return {"status": "ok", "difficulty": 2, "workflow_engine": "langgraph"}

    @app.post("/review")
    def review(payload: ExpenseRequest) -> dict:
        return run_expense_review(payload)

    return app


app = create_app()
