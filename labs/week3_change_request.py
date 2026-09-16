from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field


SECURITY_POLICY = {
    "document_id": "security-policy",
    "chunk_id": "security-policy-04",
    "text": "보안 규정 예외와 긴급 배포는 권한 있는 승인자의 검토와 기록이 필요합니다.",
}


class ChangeRequest(BaseModel):
    request: str = Field(min_length=5, max_length=500)
    user_role: str = Field(pattern="^(employee|manager)$")


def planner(payload: ChangeRequest, revision_count: int) -> dict:
    return {
        "request": payload.request,
        "required_evidence": [SECURITY_POLICY],
        "revision_count": revision_count,
        "draft": "정책과 권한을 확인한 뒤 변경안을 제시한다.",
    }


def evidence_reviewer(plan: dict) -> str:
    return "REVISE" if "무시" in plan["request"] else "PASS"


def risk_reviewer(plan: dict) -> str:
    return "HUMAN_REVIEW" if "무시" in plan["request"] else "PASS"


def synthesize(plan: dict, status: str, reason: str | None) -> dict:
    packet = None
    if status == "human_review":
        packet = {
            "request": plan["request"],
            "evidence": [{"document_id": SECURITY_POLICY["document_id"], "chunk_id": SECURITY_POLICY["chunk_id"]}],
            "reason": reason,
            "decision_needed": "승인 권한자가 정책 예외 여부를 판단",
        }
    return {"status": status, "human_review_packet": packet}


def run_change_review(payload: ChangeRequest) -> dict:
    agents = ["planner"]
    revision_count = 0
    plan = planner(payload, revision_count)

    if evidence_reviewer(plan) == "REVISE":
        revision_count = 1
        agents.extend(["evidence_reviewer", "risk_reviewer", "planner"])
        plan = planner(payload, revision_count)
    else:
        agents.extend(["evidence_reviewer", "risk_reviewer"])

    risk_status = risk_reviewer(plan)
    status = "human_review" if risk_status == "HUMAN_REVIEW" else "done"
    reason = "policy_bypass_requested" if status == "human_review" else None
    agents.append("synthesizer")
    result = synthesize(plan, status, reason)
    return {
        "difficulty": 3,
        "agents_run": agents,
        "revision_count": revision_count,
        "citations": [{"document_id": SECURITY_POLICY["document_id"], "chunk_id": SECURITY_POLICY["chunk_id"]}],
        **result,
    }


def create_app() -> FastAPI:
    app = FastAPI(title="Week 3 — Change Request Review", version="1.0.0")

    @app.get("/health")
    def health() -> dict[str, str | int]:
        return {"status": "ok", "difficulty": 3}

    @app.post("/review-change")
    def review_change(payload: ChangeRequest) -> dict:
        return run_change_review(payload)

    return app


app = create_app()
