from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field


DOCUMENTS = [
    {
        "document_id": "leave-policy",
        "chunk_id": "leave-policy-01",
        "text": "휴가 신청은 시작일 기준 최소 3일 전에 팀장 승인을 받아야 합니다.",
        "keywords": {"휴가", "신청", "며칠", "전에", "전", "해야", "하나요"},
    }
]


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=300)


def retrieve(question: str) -> list[dict]:
    tokens = set(question.replace("?", "").split())
    return [document for document in DOCUMENTS if tokens & document["keywords"]]


def answer(question: str, evidence: list[dict]) -> dict:
    if not evidence:
        return {
            "status": "insufficient_evidence",
            "answer": None,
            "citations": [],
            "reason": "no_matching_policy",
        }
    document = evidence[0]
    return {
        "status": "answered",
        "answer": document["text"],
        "citations": [{"document_id": document["document_id"], "chunk_id": document["chunk_id"]}],
        "reason": None,
    }


def create_app() -> FastAPI:
    app = FastAPI(title="Week 1 — Policy Q&A", version="1.0.0")

    @app.get("/health")
    def health() -> dict[str, str | int]:
        return {"status": "ok", "difficulty": 1}

    @app.post("/query")
    def query(payload: QueryRequest) -> dict:
        evidence = retrieve(payload.question)
        result = answer(payload.question, evidence)
        return {"difficulty": 1, "agents_run": ["retriever", "answer"], **result}

    return app


app = create_app()
