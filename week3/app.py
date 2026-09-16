from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from fastapi import FastAPI
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


class ChangeRequest(BaseModel):
    request: str = Field(min_length=5, max_length=500)
    user_role: str = Field(pattern="^(employee|manager)$")


class ChangeState(TypedDict, total=False):
    request: str
    user_role: str
    policy_docs: list[Document]
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
    page_content="보안 규정 예외와 긴급 배포는 권한 있는 승인자의 검토와 기록이 필요합니다.",
    metadata={"document_id": "security-policy", "chunk_id": "security-policy-04"},
)
SPLITTER = RecursiveCharacterTextSplitter(chunk_size=120, chunk_overlap=0)
POLICY_CHUNKS = SPLITTER.split_documents([POLICY_DOCUMENT])
policy_retrieval_chain = RunnableLambda(lambda _: POLICY_CHUNKS)


def planner_node(state: ChangeState) -> ChangeState:
    revision_count = state.get("revision_count", 0)
    if state.get("revision_requested"):
        revision_count += 1
    documents = policy_retrieval_chain.invoke(state["request"])
    return {
        "policy_docs": documents,
        "citations": [
            {
                "document_id": str(document.metadata["document_id"]),
                "chunk_id": str(document.metadata["chunk_id"]),
            }
            for document in documents
        ],
        "draft": "정책 근거와 권한을 확인한 뒤 변경안을 제시한다.",
        "revision_count": revision_count,
        "agents_run": ["planner"],
    }


def route_after_planner(state: ChangeState) -> Literal["evidence_reviewer", "synthesizer"]:
    return "synthesizer" if state.get("revision_requested") else "evidence_reviewer"


def evidence_reviewer_node(state: ChangeState) -> ChangeState:
    policy_bypass = "무시" in state["request"]
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


def build_graph():
    graph = StateGraph(ChangeState)
    graph.add_node("planner", planner_node)
    graph.add_node("evidence_reviewer", evidence_reviewer_node)
    graph.add_node("risk_reviewer", risk_reviewer_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_edge(START, "planner")
    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {"evidence_reviewer": "evidence_reviewer", "synthesizer": "synthesizer"},
    )
    graph.add_edge("evidence_reviewer", "risk_reviewer")
    graph.add_conditional_edges(
        "risk_reviewer",
        route_after_risk,
        {"planner": "planner", "synthesizer": "synthesizer"},
    )
    graph.add_edge("synthesizer", END)
    return graph.compile()


WORKFLOW = build_graph()


def run_change_review(payload: ChangeRequest) -> dict:
    state = WORKFLOW.invoke({**payload.model_dump(), "revision_count": 0, "agents_run": []})
    return {
        "difficulty": 3,
        "business_use_case": "it_change_risk_review",
        "workflow_engine": "langgraph",
        "agents_run": state["agents_run"],
        "revision_count": state["revision_count"],
        "status": state["status"],
        "citations": state["citations"],
        "human_review_packet": state["human_review_packet"],
    }


def create_app() -> FastAPI:
    app = FastAPI(title="Week 3 — LangGraph Change Review", version="2.0.0")

    @app.get("/health")
    def health() -> dict[str, str | int]:
        return {"status": "ok", "difficulty": 3, "workflow_engine": "langgraph"}

    @app.post("/review-change")
    def review_change(payload: ChangeRequest) -> dict:
        return run_change_review(payload)

    return app


app = create_app()
