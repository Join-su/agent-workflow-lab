from __future__ import annotations

import operator
from dataclasses import dataclass
from typing import Annotated, Callable, Literal, Protocol, TypedDict

from fastapi import FastAPI
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from lab_core import FixtureRetriever, build_live_adapters, citations, resolve_mode, source_context


POLICY_SOURCE_DOCUMENTS = [
    Document(
        page_content="Vacation requests must be submitted at least three business days before the start date. Employees should include the requested dates and coverage notes.",
        metadata={"document_id": "hr-leave-policy"},
    ),
    Document(
        page_content="Managers approve vacation requests after reviewing team coverage. The assistant only explains policy and never submits or approves leave.",
        metadata={"document_id": "hr-leave-policy"},
    ),
]


def split_policy_documents(
    documents: list[Document], *, chunk_size: int = 100
) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=15)
    chunks = splitter.split_documents(documents)
    for index, chunk in enumerate(chunks, start=1):
        chunk.metadata["chunk_id"] = f"hr-leave-policy-{index:02d}"
    return chunks


POLICY_DOCUMENTS = split_policy_documents(POLICY_SOURCE_DOCUMENTS)


class Retriever(Protocol):
    def search(self, query: str, *, k: int = 3, filter: dict | None = None) -> list[Document]: ...


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


def create_fixture_services() -> PolicyServices:
    def grounded_answer(_: str, documents: list[Document]) -> str:
        return documents[0].page_content

    return PolicyServices(FixtureRetriever(POLICY_DOCUMENTS), grounded_answer, "fixture")


def create_live_services() -> PolicyServices:
    retriever, model = build_live_adapters(
        collection_name="week1_hr_policy", documents=POLICY_DOCUMENTS
    )

    def answer(question: str, documents: list[Document]) -> str:
        return model.text(
            "Answer only from the HR policy context. If context is insufficient, say so.\n"
            f"Context:\n{source_context(documents)}\nQuestion: {question}"
        )

    return PolicyServices(retriever, answer, "live")


def build_workflow(services: PolicyServices):
    def retrieve(state: QueryState) -> QueryState:
        return {"documents": services.retriever.search(state["question"]), "steps": ["retrieve"]}

    def answer(state: QueryState) -> QueryState:
        documents = state["documents"]
        return {
            "answer": services.answer(state["question"], documents) if documents else None,
            "steps": ["answer"],
        }

    def guard(state: QueryState) -> QueryState:
        documents = state["documents"]
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

    @api.get("/health")
    def health() -> dict:
        return {"status": "ok", "difficulty": 1, "mode": services.mode}

    @api.post("/query")
    def query(payload: QueryRequest) -> dict:
        return run_policy_query(payload.question, services)

    return api


app = create_app()
