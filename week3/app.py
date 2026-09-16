from __future__ import annotations

import operator
from dataclasses import dataclass
from typing import Annotated, Callable, Literal, Protocol, TypedDict

from fastapi import FastAPI
from langchain_core.documents import Document
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from lab_core import FixtureRetriever, build_live_adapters, citations, resolve_mode, source_context


RUNBOOKS = [
    Document(
        page_content="For checkout errors after deployment, compare the deployment timestamp, error rate, and rollback readiness. SEV1 changes require incident commander approval.",
        metadata={"document_id": "checkout-incident-runbook", "chunk_id": "checkout-runbook-01"},
    ),
    Document(
        page_content="For elevated search latency, inspect cache metrics and recent changes. Prefer observation and reversible mitigations.",
        metadata={"document_id": "catalog-incident-runbook", "chunk_id": "catalog-runbook-01"},
    ),
]


class Retriever(Protocol):
    def search(self, query: str, *, k: int = 3) -> list[Document]: ...


class IncidentRequest(BaseModel):
    service: str = Field(min_length=2, max_length=80)
    summary: str = Field(min_length=5, max_length=1000)
    severity: Literal["SEV1", "SEV2", "SEV3"]


class TriageDecision(BaseModel):
    suspected_change_related: bool
    objective: str


class CommandProposal(BaseModel):
    command: str
    purpose: str
    dry_run: bool = True


@dataclass
class IncidentServices:
    retriever: Retriever
    triage: Callable[[IncidentRequest], TriageDecision]
    investigate: Callable[[IncidentRequest, list[Document]], str]
    command: Callable[[IncidentRequest, str, bool], list[CommandProposal]]
    mode: Literal["fixture", "live"]


class IncidentState(TypedDict, total=False):
    incident: IncidentRequest
    triage: TriageDecision
    documents: list[Document]
    findings: str
    proposals: list[CommandProposal]
    revision_count: int
    max_revisions: int
    needs_revision: bool
    status: str
    approval_packet: dict | None
    observation_plan: dict | None
    agents_run: Annotated[list[str], operator.add]


def create_fixture_services() -> IncidentServices:
    def triage(incident: IncidentRequest) -> TriageDecision:
        return TriageDecision(
            suspected_change_related="after" in incident.summary.lower() or "deployment" in incident.summary.lower(),
            objective="stabilize service while preserving evidence",
        )

    def investigate(incident: IncidentRequest, documents: list[Document]) -> str:
        runbook = documents[0].metadata["chunk_id"] if documents else "no-matching-runbook"
        return f"Correlate {incident.service} symptoms with recent changes using {runbook}."

    def command(incident: IncidentRequest, _: str, revised: bool) -> list[CommandProposal]:
        if incident.severity == "SEV1" and not revised:
            return [CommandProposal(command="kubectl rollout undo deployment/checkout", purpose="candidate rollback", dry_run=False)]
        if incident.severity == "SEV1":
            return [
                CommandProposal(
                    command="kubectl rollout status deployment/checkout",
                    purpose="observe rollout status",
                )
            ]
        return [CommandProposal(command=f"observe {incident.service} metrics", purpose="gather non-invasive evidence")]

    return IncidentServices(FixtureRetriever(RUNBOOKS), triage, investigate, command, "fixture")


def create_live_services() -> IncidentServices:
    retriever, model = build_live_adapters(collection_name="week3_incident_runbooks", documents=RUNBOOKS)

    def triage(incident: IncidentRequest) -> TriageDecision:
        return model.structured(
            TriageDecision,
            "Triage the incident without executing actions.\n"
            f"Service: {incident.service}\nSeverity: {incident.severity}\nSummary: {incident.summary}",
        )

    def investigate(incident: IncidentRequest, documents: list[Document]) -> str:
        return model.text(
            "Act as an investigator. Produce evidence checks only, grounded in the runbook.\n"
            f"Runbook:\n{source_context(documents)}\nIncident: {incident.model_dump()}"
        )

    def command(incident: IncidentRequest, findings: str, revised: bool) -> list[CommandProposal]:
        class ProposalSet(BaseModel):
            proposals: list[CommandProposal]

        result = model.structured(
            ProposalSet,
            "Propose commands for human review only. Every command must be non-destructive and dry_run=true. "
            "Never claim execution.\n"
            f"Revised: {revised}\nIncident: {incident.model_dump()}\nFindings: {findings}",
        )
        return result.proposals

    return IncidentServices(retriever, triage, investigate, command, "live")


def build_workflow(services: IncidentServices):
    def proposal_is_safe(proposal: CommandProposal) -> bool:
        command = proposal.command.strip().lower()
        read_only_prefixes = (
            "observe ",
            "kubectl get ",
            "kubectl describe ",
            "kubectl logs ",
            "kubectl rollout status ",
        )
        shell_control = (";", "&", "|", "`", "$", "<", ">", "\\", "\n", "\r")
        return (
            proposal.dry_run
            and not any(marker in command for marker in shell_control)
            and command.startswith(read_only_prefixes)
        )

    def triage_agent(state: IncidentState) -> IncidentState:
        incident = state["incident"]
        return {
            "triage": services.triage(incident),
            "documents": services.retriever.search(f"{incident.service} {incident.summary}", k=2),
            "agents_run": ["triage_agent"],
        }

    def investigator_agent(state: IncidentState) -> IncidentState:
        return {
            "findings": services.investigate(state["incident"], state["documents"]),
            "agents_run": ["investigator_agent"],
        }

    def commander_agent(state: IncidentState) -> IncidentState:
        revised = state["revision_count"] > 0
        return {
            "proposals": services.command(state["incident"], state["findings"], revised),
            "agents_run": ["commander_agent"],
        }

    def risk_guard(state: IncidentState) -> IncidentState:
        unsafe = not state["proposals"] or any(
            not proposal_is_safe(proposal) for proposal in state["proposals"]
        )
        can_revise = state["revision_count"] < state["max_revisions"]
        if unsafe and can_revise:
            return {"needs_revision": True, "revision_count": state["revision_count"] + 1, "agents_run": ["risk_guard"]}
        if unsafe:
            return {
                "needs_revision": False,
                "status": "blocked_manual_review",
                "approval_packet": {
                    "objective": state["triage"].objective,
                    "findings": state["findings"],
                    "citations": citations(state["documents"]),
                    "proposed_commands": [],
                    "rejected_unsafe_proposals": [
                        proposal.model_dump() for proposal in state["proposals"]
                    ],
                },
                "agents_run": ["risk_guard"],
            }
        incident = state["incident"]
        packet = None
        observation_plan = None
        status = "plan_ready"
        if incident.severity in {"SEV1", "SEV2"}:
            status = "human_approval_required"
            packet = {
                "objective": state["triage"].objective,
                "findings": state["findings"],
                "citations": citations(state["documents"]),
                "proposed_commands": [proposal.model_dump() for proposal in state["proposals"]],
            }
        else:
            observation_plan = {
                "objective": state["triage"].objective,
                "findings": state["findings"],
                "citations": citations(state["documents"]),
                "proposed_commands": [proposal.model_dump() for proposal in state["proposals"]],
            }
        return {
            "needs_revision": False,
            "status": status,
            "approval_packet": packet,
            "observation_plan": observation_plan,
            "agents_run": ["risk_guard"],
        }

    def after_guard(state: IncidentState) -> Literal["revise", "finish"]:
        return "revise" if state["needs_revision"] else "finish"

    graph = StateGraph(IncidentState)
    graph.add_node("triage_agent", triage_agent)
    graph.add_node("investigator_agent", investigator_agent)
    graph.add_node("commander_agent", commander_agent)
    graph.add_node("risk_guard", risk_guard)
    graph.add_edge(START, "triage_agent")
    graph.add_edge("triage_agent", "investigator_agent")
    graph.add_edge("investigator_agent", "commander_agent")
    graph.add_edge("commander_agent", "risk_guard")
    graph.add_conditional_edges("risk_guard", after_guard, {"revise": "commander_agent", "finish": END})
    return graph.compile()


def run_incident_response(incident: IncidentRequest, services: IncidentServices | None = None) -> dict:
    services = services or create_fixture_services()
    state = build_workflow(services).invoke(
        {"incident": incident, "revision_count": 0, "max_revisions": 1, "agents_run": []}
    )
    return {
        "difficulty": 3,
        "business_use_case": "production_incident_response_command_system",
        "mode": services.mode,
        "status": state["status"],
        "revision_count": state["revision_count"],
        "max_revisions": state["max_revisions"],
        "agents_run": state["agents_run"],
        "citations": citations(state["documents"]),
        "approval_packet": state.get("approval_packet"),
        "observation_plan": state.get("observation_plan"),
        "executed_commands": [],
    }


def create_app(services: IncidentServices | None = None, *, mode: str | None = None) -> FastAPI:
    selected_mode = resolve_mode(mode)
    if services is None:
        services = create_live_services() if selected_mode == "live" else create_fixture_services()
    api = FastAPI(title="Week 3 — Incident Response Command System", version="3.0.0")

    @api.get("/health")
    def health() -> dict:
        return {"status": "ok", "difficulty": 3, "mode": services.mode}

    @api.post("/incidents/respond")
    def respond(payload: IncidentRequest) -> dict:
        return run_incident_response(payload, services)

    return api


app = create_app()
