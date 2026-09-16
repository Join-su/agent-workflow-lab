from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field


EXPENSE_POLICY = {
    "document_id": "expense-policy",
    "chunk_id": "expense-policy-02",
    "text": "출장비 정산에는 영수증과 업무 목적이 필요하며, 영수증이 없으면 보완 요청으로 처리합니다.",
}


class ExpenseRequest(BaseModel):
    amount: int = Field(gt=0, le=1_000_000)
    receipt_attached: bool
    purpose: str = Field(min_length=3, max_length=80)


def retrieve_policy(_: ExpenseRequest) -> dict:
    return EXPENSE_POLICY


def policy_reviewer(payload: ExpenseRequest, evidence: dict) -> dict:
    missing: list[str] = []
    if not payload.receipt_attached:
        missing.append("receipt_required")
    if not payload.purpose.strip():
        missing.append("purpose_required")
    return {"evidence": evidence, "missing": missing}


def risk_router(review: dict) -> dict:
    if review["missing"]:
        return {"status": "clarify", "required_follow_up": review["missing"][0]}
    return {"status": "approved_for_next_step", "required_follow_up": None}


def create_app() -> FastAPI:
    app = FastAPI(title="Week 2 — Expense Review", version="1.0.0")

    @app.get("/health")
    def health() -> dict[str, str | int]:
        return {"status": "ok", "difficulty": 2}

    @app.post("/review")
    def review(payload: ExpenseRequest) -> dict:
        evidence = retrieve_policy(payload)
        reviewed = policy_reviewer(payload, evidence)
        routed = risk_router(reviewed)
        return {
            "difficulty": 2,
            "agents_run": ["retriever", "policy_reviewer", "risk_router"],
            "citations": [{"document_id": evidence["document_id"], "chunk_id": evidence["chunk_id"]}],
            **routed,
        }

    return app


app = create_app()
