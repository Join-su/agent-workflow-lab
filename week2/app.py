from __future__ import annotations

import operator
from dataclasses import dataclass
from typing import Annotated, Callable, Literal, Protocol, TypedDict

from fastapi import FastAPI
from langchain_core.documents import Document
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from lab_core import FixtureRetriever, build_live_adapters, citations, resolve_mode, source_context


SUPPORT_PLAYBOOKS = [
    Document(
        page_content="For duplicate charges, verify invoice IDs and payment timestamps, then prepare a billing refund review.",
        metadata={"document_id": "support-billing-playbook", "chunk_id": "support-billing-01", "category": "billing"},
    ),
    Document(
        page_content="If all users are blocked or service is down, preserve evidence and escalate to incident response immediately.",
        metadata={"document_id": "support-incident-playbook", "chunk_id": "support-incident-01", "category": "technical"},
    ),
    Document(
        page_content="For login failures, confirm account identity and collect the error timestamp before access troubleshooting.",
        metadata={"document_id": "support-access-playbook", "chunk_id": "support-access-01", "category": "access"},
    ),
]


class Retriever(Protocol):
    def search(self, query: str, *, k: int = 3, filter: dict | None = None) -> list[Document]: ...


class TicketRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=5, max_length=1000)
    customer_tier: Literal["standard", "enterprise"]


class TicketClassification(BaseModel):
    category: Literal["billing", "access", "technical", "other"]
    priority: Literal["normal", "urgent"]


@dataclass
class TicketServices:
    retriever: Retriever
    classify: Callable[[TicketRequest], TicketClassification]
    plan: Callable[[TicketRequest, TicketClassification, list[Document]], str]
    mode: Literal["fixture", "live"]


class TicketState(TypedDict, total=False):
    ticket: TicketRequest
    classification: TicketClassification
    documents: list[Document]
    resolution_plan: str
    route: str
    status: str
    steps: Annotated[list[str], operator.add]


def create_fixture_services() -> TicketServices:
    def classify(ticket: TicketRequest) -> TicketClassification:
        text = f"{ticket.subject} {ticket.description}".lower()
        urgent = any(term in text for term in ("outage", "service is down", "all users", "blocked"))
        if any(term in text for term in ("invoice", "charged", "refund", "billing")):
            category = "billing"
        elif any(term in text for term in ("login", "password", "account")):
            category = "access"
        elif urgent or any(term in text for term in ("error", "latency", "service")):
            category = "technical"
        else:
            category = "other"
        return TicketClassification(category=category, priority="urgent" if urgent else "normal")

    def plan(_: TicketRequest, classification: TicketClassification, documents: list[Document]) -> str:
        if documents:
            return f"Follow {documents[0].metadata['chunk_id']} and keep a human support owner on the case."
        return f"Collect missing details before routing the {classification.category} ticket."

    return TicketServices(FixtureRetriever(SUPPORT_PLAYBOOKS), classify, plan, "fixture")


def create_live_services() -> TicketServices:
    retriever, model = build_live_adapters(
        collection_name="week2_support_playbooks", documents=SUPPORT_PLAYBOOKS
    )

    def classify(ticket: TicketRequest) -> TicketClassification:
        return model.structured(
            TicketClassification,
            "Classify this support ticket. Urgent means a broad outage or users blocked.\n"
            f"Subject: {ticket.subject}\nDescription: {ticket.description}",
        )

    def plan(ticket: TicketRequest, classification: TicketClassification, documents: list[Document]) -> str:
        return model.text(
            "Draft a read-only support resolution plan grounded only in the playbook. Do not claim an action ran.\n"
            f"Classification: {classification.model_dump()}\nPlaybook:\n{source_context(documents)}\n"
            f"Ticket: {ticket.description}"
        )

    return TicketServices(retriever, classify, plan, "live")


def build_workflow(services: TicketServices):
    def classify(state: TicketState) -> TicketState:
        return {"classification": services.classify(state["ticket"]), "steps": ["classify"]}

    def retrieve(state: TicketState) -> TicketState:
        ticket, classification = state["ticket"], state["classification"]
        query = f"{classification.category} {ticket.subject} {ticket.description}"
        return {
            "documents": services.retriever.search(
                query, k=2, filter={"category": classification.category}
            ),
            "steps": ["retrieve_playbook"],
        }

    def plan(state: TicketState) -> TicketState:
        documents = state["documents"]
        if not documents:
            category = state["classification"].category
            return {
                "resolution_plan": f"Collect missing details before routing the {category} ticket.",
                "steps": ["plan_resolution"],
            }
        return {
            "resolution_plan": services.plan(state["ticket"], state["classification"], documents),
            "steps": ["plan_resolution"],
        }

    def route(state: TicketState) -> TicketState:
        classification = state["classification"]
        destination = "incident_escalation" if classification.priority == "urgent" else {
            "billing": "billing_queue", "access": "access_queue", "technical": "technical_queue", "other": "general_queue"
        }[classification.category]
        status = "plan_ready" if state["documents"] else "needs_more_information"
        return {"route": destination, "status": status, "steps": ["route"]}

    def route_destination(state: TicketState) -> str:
        return state["route"]

    def queue_node(name: str):
        def enter_queue(_: TicketState) -> TicketState:
            return {"steps": [name]}

        return enter_queue

    graph = StateGraph(TicketState)
    for name, node in (("classify", classify), ("retrieve_playbook", retrieve), ("plan_resolution", plan), ("route", route)):
        graph.add_node(name, node)
    destinations = ("incident_escalation", "billing_queue", "access_queue", "technical_queue", "general_queue")
    for destination in destinations:
        graph.add_node(destination, queue_node(destination))
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "retrieve_playbook")
    graph.add_edge("retrieve_playbook", "plan_resolution")
    graph.add_edge("plan_resolution", "route")
    graph.add_conditional_edges("route", route_destination, {name: name for name in destinations})
    for destination in destinations:
        graph.add_edge(destination, END)
    return graph.compile()


def run_ticket_workflow(ticket: TicketRequest, services: TicketServices | None = None) -> dict:
    services = services or create_fixture_services()
    state = build_workflow(services).invoke({"ticket": ticket, "steps": []})
    classification = state["classification"]
    return {
        "difficulty": 2,
        "business_use_case": "support_ticket_resolution_planning",
        "mode": services.mode,
        "status": state["status"],
        "category": classification.category,
        "priority": classification.priority,
        "route": state["route"],
        "resolution_plan": state["resolution_plan"],
        "citations": citations(state["documents"]),
        "steps": state["steps"],
    }


def create_app(services: TicketServices | None = None, *, mode: str | None = None) -> FastAPI:
    selected_mode = resolve_mode(mode)
    if services is None:
        services = create_live_services() if selected_mode == "live" else create_fixture_services()
    api = FastAPI(title="Week 2 — Support Ticket Resolution Planner", version="3.0.0")

    @api.get("/health")
    def health() -> dict:
        return {"status": "ok", "difficulty": 2, "mode": services.mode}

    @api.post("/tickets/plan")
    def plan_ticket(payload: TicketRequest) -> dict:
        return run_ticket_workflow(payload, services)

    return api


app = create_app()
