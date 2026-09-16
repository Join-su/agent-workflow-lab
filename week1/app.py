from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from fastapi import FastAPI
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=300)


class QueryState(TypedDict, total=False):
    question: str
    retrieved_docs: list[Document]
    answer: str | None
    citations: list[dict[str, str]]
    status: str
    reason: str | None
    agents_run: Annotated[list[str], operator.add]


SOURCE_DOCUMENT = Document(
    page_content="휴가 신청은 시작일 기준 최소 3일 전에 팀장 승인을 받아야 합니다.",
    metadata={"document_id": "leave-policy", "chunk_id": "leave-policy-01"},
)
SPLITTER = RecursiveCharacterTextSplitter(chunk_size=120, chunk_overlap=0)
POLICY_CHUNKS = SPLITTER.split_documents([SOURCE_DOCUMENT])


def _retrieve_documents(question: str) -> list[Document]:
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
    return {
        "answer": document.page_content,
        "citations": [
            {
                "document_id": str(document.metadata["document_id"]),
                "chunk_id": str(document.metadata["chunk_id"]),
            }
        ],
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
        "business_use_case": "hr_leave_policy_self_service",
        "workflow_engine": "langgraph",
        "agents_run": state["agents_run"],
        "status": state["status"],
        "answer": state["answer"],
        "citations": state["citations"],
        "reason": state["reason"],
    }


def create_app() -> FastAPI:
    app = FastAPI(title="Week 1 — LangChain Policy Q&A", version="2.0.0")

    @app.get("/health")
    def health() -> dict[str, str | int]:
        return {"status": "ok", "difficulty": 1, "workflow_engine": "langgraph"}

    @app.post("/query")
    def query(payload: QueryRequest) -> dict:
        return run_query(payload.question)

    return app


app = create_app()
