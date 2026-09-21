from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from fastapi import FastAPI, HTTPException
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, ValidationError
from shared.live_rag import (
    WEEK_COLLECTIONS,
    LiveRagError,
    citations_for,
    collection_diagnostics,
    generate_grounded_text,
    generate_structured,
    is_live_mode,
    retrieve_documents_with_trace,
)


class ExpenseRequest(BaseModel):
    amount: int = Field(gt=0, le=1_000_000)
    receipt_attached: bool
    purpose: str = Field(min_length=3, max_length=80)


class ExpenseClassification(BaseModel):
    """The only judgement the model is allowed to make, as a closed value set."""

    category: Literal["transport", "lodging", "meal", "other"]
    priority: Literal["normal", "urgent"]
    reason: str = Field(min_length=1, max_length=200)


class ExpenseState(TypedDict, total=False):
    amount: int
    receipt_attached: bool
    purpose: str
    category: str
    priority: str
    classification_reason: str
    policy_docs: list[Document]
    retrieval_trace: list[dict[str, str | float | bool]]
    missing: list[str]
    citations: list[dict[str, str]]
    required_follow_up: str | None
    route: Literal["clarify", "manager_review", "next_step", "insufficient_evidence"]
    status: str
    review_summary: str | None
    agents_run: Annotated[list[str], operator.add]


# Fixture sources mirror the category split of knowledge/week2 so the metadata
# filter is observable without a database.
SOURCE_DOCUMENTS = [
    Document(
        page_content="국내 교통비는 실비로 청구하며 예약 내역과 결제 영수증을 함께 첨부합니다.",
        metadata={"document_id": "transport-expense-playbook", "category": "transport"},
    ),
    Document(
        page_content="국내 숙박비는 1박당 상한 120,000원이며 영수증에 투숙자와 일자가 보여야 합니다.",
        metadata={"document_id": "lodging-expense-playbook", "category": "lodging"},
    ),
    Document(
        page_content="출장 중 식대는 1인 1식 20,000원을 상한으로 하며 결제 일시가 보여야 합니다.",
        metadata={"document_id": "meal-expense-playbook", "category": "meal"},
    ),
    Document(
        page_content="출장비 사전 검토에는 영수증과 업무 목적이 필요하며, 영수증이 없으면 receipt_required 보완 요청으로 처리합니다.",
        metadata={"document_id": "expense-policy", "category": "other"},
    ),
]
SPLITTER = RecursiveCharacterTextSplitter(chunk_size=120, chunk_overlap=0)
POLICY_CHUNKS = SPLITTER.split_documents(SOURCE_DOCUMENTS)
for _index, _chunk in enumerate(POLICY_CHUNKS, start=1):
    _chunk.metadata["chunk_id"] = f"{_chunk.metadata['document_id']}-{_index:03d}"

CATEGORY_KEYWORDS = {
    "transport": ("교통", "택시", "기차", "철도", "버스", "주유", "통행료", "항공"),
    "lodging": ("숙박", "호텔", "숙소", "모텔", "게스트하우스"),
    "meal": ("식대", "식사", "점심", "저녁", "중식", "석식"),
}
URGENT_KEYWORDS = ("긴급", "즉시", "당일")
URGENT_AMOUNT = 500_000
MAX_CLASSIFICATION_REASON = 200


def classify_expense_fixture(payload: ExpenseRequest) -> ExpenseClassification:
    """Deterministic stand-in for the model's structured judgement."""
    category = "other"
    for name, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in payload.purpose for keyword in keywords):
            category = name
            break
    urgent = payload.amount >= URGENT_AMOUNT or any(
        keyword in payload.purpose for keyword in URGENT_KEYWORDS
    )
    return ExpenseClassification(
        category=category,
        priority="urgent" if urgent else "normal",
        reason=f"업무 목적과 금액({payload.amount}원)을 기준으로 분류했습니다.",
    )


def classify_expense(payload: ExpenseRequest) -> ExpenseClassification:
    """Return a validated classification, never a guessed fallback category."""
    if not is_live_mode():
        return classify_expense_fixture(payload)
    raw = generate_structured(
        ExpenseClassification,
        "Classify the travel expense claim into a policy category and priority.",
        f"금액: {payload.amount}원 / 영수증 첨부: {payload.receipt_attached} / 목적: {payload.purpose}",
    )
    try:
        return ExpenseClassification.model_validate(
            raw if isinstance(raw, dict) else raw.model_dump() 
            # 직렬화 라기 보단 dict화 (직렬화는 model_dump_json : 문자열)
        )
    except ValidationError as error:
        # An out-of-schema category must surface, not become "other" silently.
        raise LiveRagError("분류 결과가 허용된 category·priority 집합을 벗어났습니다.") from error


def _retrieve_fixture_documents(purpose: str, category: str) -> list[Document]:
    """Fixture-only retrieval. The live path runs in ``policy_retriever_node``."""
    return [chunk for chunk in POLICY_CHUNKS if chunk.metadata["category"] == category]


policy_retrieval_chain = RunnableLambda(
    lambda inputs: _retrieve_fixture_documents(inputs["purpose"], inputs["category"])
)


def classifier_node(state: ExpenseState) -> ExpenseState:
    classification = classify_expense(
        ExpenseRequest(
            amount=state["amount"],
            receipt_attached=state["receipt_attached"],
            purpose=state["purpose"],
        )
    )
    return {
        "category": classification.category,
        "priority": classification.priority,
        "classification_reason": classification.reason,
        "agents_run": ["classifier"],
    }


def policy_retriever_node(state: ExpenseState) -> ExpenseState:
    # The classified category filters candidates before similarity ranking, so a
    # lodging claim can never cite the transport playbook.
    if is_live_mode():
        documents, retrieval_trace = retrieve_documents_with_trace(
            WEEK_COLLECTIONS["week2"],
            state["purpose"],
            metadata_filter={"category": state["category"]},
        )
    else:
        documents = policy_retrieval_chain.invoke(
            {"purpose": state["purpose"], "category": state["category"]}
        )
        retrieval_trace = []
    return {
        "policy_docs": documents,
        "citations": citations_for(documents),
        "retrieval_trace": retrieval_trace,
        "agents_run": ["policy_retriever"],
    }


def evidence_extractor_node(state: ExpenseState) -> ExpenseState:
    # A deterministic rule, not a model judgement: evidence either exists or not.
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
    if state["priority"] == "urgent":
        return {
            "route": "manager_review",
            "required_follow_up": "manager_approval_required",
            "agents_run": ["risk_router"],
        }
    return {
        "route": "next_step",
        "required_follow_up": None,
        "agents_run": ["risk_router"],
    }


def route_after_review(state: ExpenseState) -> Literal[
    "clarify", "manager_review", "next_step", "insufficient_evidence"
]:
    return state["route"]


# Terminal nodes record themselves so the response trace shows the chosen branch.
def clarify_node(_: ExpenseState) -> ExpenseState:
    return {"status": "clarify", "agents_run": ["clarify"]}


def manager_review_node(_: ExpenseState) -> ExpenseState:
    return {"status": "manager_review", "agents_run": ["manager_review"]}


def next_step_node(_: ExpenseState) -> ExpenseState:
    return {"status": "approved_for_next_step", "agents_run": ["next_step"]}


def insufficient_evidence_node(_: ExpenseState) -> ExpenseState:
    return {"status": "insufficient_evidence", "agents_run": ["insufficient_evidence"]}


def build_graph():
    graph = StateGraph(ExpenseState)
    graph.add_node("classifier", classifier_node) # 카테고리 분류
    graph.add_node("policy_retriever", policy_retriever_node) # 분류된 카테고리를 필터로 사용해 DB에서 검색시작
    graph.add_node("evidence_extractor", evidence_extractor_node) 
    graph.add_node("policy_reviewer", policy_reviewer_node) # 리트리버된 문서와 질문을 토대로 형식에 맞는 결과 도출
    graph.add_node("risk_router", risk_router_node) # 갈림길
    graph.add_node("clarify", clarify_node)
    graph.add_node("manager_review", manager_review_node)
    graph.add_node("next_step", next_step_node)
    graph.add_node("insufficient_evidence", insufficient_evidence_node)
    graph.add_edge(START, "classifier")
    graph.add_edge("classifier", "policy_retriever")
    graph.add_edge("policy_retriever", "evidence_extractor")
    graph.add_edge("evidence_extractor", "policy_reviewer")
    graph.add_edge("policy_reviewer", "risk_router")
    graph.add_conditional_edges(
        "risk_router",
        route_after_review, # literal 검증
        {
            "clarify": "clarify",
            "manager_review": "manager_review",
            "next_step": "next_step",
            "insufficient_evidence": "insufficient_evidence",
        },
    )
    for terminal in ("clarify", "manager_review", "next_step", "insufficient_evidence"):
        graph.add_edge(terminal, END)
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
        "category": state["category"],
        "priority": state["priority"],
        "classification_reason": state["classification_reason"],
        "required_follow_up": state["required_follow_up"],
        "citations": state["citations"],
        "retrieval_trace": state.get("retrieval_trace", []),
        "review_summary": state.get("review_summary"),
    }


def create_app() -> FastAPI:
    app = FastAPI(title="Week 2 — LangChain Expense Review", version="3.0.0")

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
            return run_expense_review(payload) # graph 노드들을 모두 거쳐나온 결과
        except LiveRagError as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "live_rag_unavailable", "message": str(error)},
            ) from error

    return app


app = create_app()
