from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from fastapi import FastAPI, HTTPException
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from shared.live_rag import (
    WEEK_COLLECTIONS,
    LiveRagError,
    citations_for,
    collection_diagnostics,
    generate_grounded_text,
    is_live_mode,
    retrieve_documents_with_trace,
)


class ChangeRequest(BaseModel):
    request: str = Field(min_length=5, max_length=500)
    user_role: str = Field(pattern="^(employee|manager)$")
    severity: Literal["SEV1", "SEV2", "SEV3"] = "SEV3"


class CommandProposal(BaseModel):
    """A command the workflow may show a human. It is never executed."""

    command: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=200)
    dry_run: bool = True


class ChangeState(TypedDict, total=False):
    request: str
    user_role: str
    severity: str
    policy_docs: list[Document]
    retrieval_trace: list[dict[str, str | float | bool]]
    citations: list[dict[str, str]]
    draft: str
    proposals: list[CommandProposal]
    # Decided per pass, so the guard judges only the current proposals.
    rejected_proposals: list[dict[str, str]]
    # Accumulated across passes, so a reviewer sees what the loop already refused.
    rejected_history: Annotated[list[dict[str, str]], operator.add]
    revision_count: int
    revision_requested: bool
    policy_bypass: bool
    status: str
    reason: str | None
    approval_packet: dict | None
    observation_plan: dict | None
    agents_run: Annotated[list[str], operator.add]


POLICY_DOCUMENT = Document(
    page_content="보안 제어 우회, 정책 예외, 긴급 배포는 자동 승인하지 않고 권한 있는 승인자의 검토와 기록이 필요합니다.",
    metadata={"document_id": "security-policy", "chunk_id": "security-policy-04"},
)
SPLITTER = RecursiveCharacterTextSplitter(chunk_size=120, chunk_overlap=0)
POLICY_CHUNKS = SPLITTER.split_documents([POLICY_DOCUMENT])

BYPASS_PHRASES = ("무시", "우회", "예외", "긴급 배포", "긴급 권한")

# Read-only verbs only. Anything that changes state stays off this list.
OBSERVATION_ALLOWLIST = (
    "kubectl get",
    "kubectl describe",
    "kubectl logs",
    "kubectl top",
    "observe",
)
# Shell metacharacters let an allowlisted prefix carry a second, unchecked command.
SHELL_CONTROL_CHARACTERS = (";", "&", "|", ">", "<", "`", "$", "\\", "\n", "\r")
MAX_REVISIONS = 1
APPROVAL_SEVERITIES = ("SEV1", "SEV2")


def proposal_is_safe(proposal: CommandProposal) -> bool:
    """Decide safety from the command text itself, never from the model's flag.

    ``dry_run`` is advisory metadata a model can set freely, so it is recorded
    but cannot make an unlisted or compound command acceptable.
    """
    command = proposal.command.strip()
    if any(character in command for character in SHELL_CONTROL_CHARACTERS):
        return False
    return any(command.startswith(prefix) for prefix in OBSERVATION_ALLOWLIST)


def propose_commands(state: ChangeState) -> list[CommandProposal]:
    """Produce observation-only proposals for the reviewer to inspect.

    The first pass of a policy-bypass request deliberately yields an unsafe
    proposal so the bounded revision loop is exercised end to end.
    """
    if state.get("policy_bypass") and not state.get("revision_requested"):
        return [
            CommandProposal(
                command="kubectl delete namespace production",
                purpose="요청자가 제시한 즉시 조치",
                dry_run=True,
            )
        ]
    return [
        CommandProposal(
            command=f"kubectl get events -n {state.get('severity', 'SEV3').lower()}",
            purpose="변경 전 상태 관찰",
            dry_run=True,
        )
    ]


def _retrieve_fixture_documents(request: str) -> list[Document]:
    """Fixture-only retrieval. The live path runs in ``planner_node``."""
    return POLICY_CHUNKS


policy_retrieval_chain = RunnableLambda(_retrieve_fixture_documents)


def planner_node(state: ChangeState) -> ChangeState:
    revision_count = state.get("revision_count", 0)
    if state.get("revision_requested"):
        revision_count += 1
    if is_live_mode():
        documents, retrieval_trace = retrieve_documents_with_trace(
            WEEK_COLLECTIONS["week3"], state["request"]
        )
    else:
        documents = policy_retrieval_chain.invoke(state["request"])
        retrieval_trace = []
    policy_bypass = any(phrase in state["request"] for phrase in BYPASS_PHRASES)
    return {
        "policy_docs": documents,
        "citations": citations_for(documents),
        "retrieval_trace": retrieval_trace,
        "policy_bypass": policy_bypass,
        "draft": (
            generate_grounded_text(
                state["request"],
                documents,
                task="Draft a Korean IT change-review plan grounded in the evidence. Do not execute changes.",
            )
            if is_live_mode() and documents
            else "정책 근거와 권한을 확인한 뒤 변경안을 제시한다."
        ),
        "proposals": propose_commands({**state, "policy_bypass": policy_bypass}),
        "revision_count": revision_count,
        "agents_run": ["planner"],
    }


def route_after_planner(state: ChangeState) -> Literal["evidence_reviewer", "insufficient_evidence"]:
    if not state["policy_docs"]:
        return "insufficient_evidence"
    return "evidence_reviewer"


def evidence_reviewer_node(state: ChangeState) -> ChangeState:
    # Every proposal is re-checked deterministically on each pass through the loop.
    rejected = [
        {"command": proposal.command, "purpose": proposal.purpose}
        for proposal in state["proposals"]
        if not proposal_is_safe(proposal)
    ]
    return {
        "rejected_proposals": rejected,
        "rejected_history": rejected,
        "agents_run": ["evidence_reviewer"],
    }


def risk_guard_node(state: ChangeState) -> ChangeState:
    unsafe = bool(state["rejected_proposals"]) or not state["proposals"]
    can_revise = state["revision_count"] < MAX_REVISIONS
    if unsafe and can_revise:
        return {
            "revision_requested": True,
            "reason": "unsafe_command_proposed",
            "agents_run": ["risk_guard"],
        }
    return {
        "revision_requested": False,
        "reason": (
            "policy_bypass_requested"
            if state["policy_bypass"]
            else ("unsafe_command_proposed" if unsafe else None)
        ),
        "agents_run": ["risk_guard"],
    }


def route_after_risk(state: ChangeState) -> Literal["planner", "blocked", "synthesizer"]:
    if state["revision_requested"]:
        return "planner"
    if state["rejected_proposals"] or not state["proposals"]:
        return "blocked"
    return "synthesizer"


def synthesizer_node(state: ChangeState) -> ChangeState:
    safe_commands = [
        {"command": proposal.command, "purpose": proposal.purpose, "dry_run": proposal.dry_run}
        for proposal in state["proposals"]
        if proposal_is_safe(proposal)
    ]
    packet = {
        "request": state["request"],
        "evidence": state["citations"],
        "reason": state["reason"],
        "proposed_commands": safe_commands,
        "rejected_unsafe_proposals": state["rejected_history"],
        "decision_needed": "승인 권한자가 관찰 계획 실행 여부를 판단",
    }
    if state["severity"] in APPROVAL_SEVERITIES or state["policy_bypass"]:
        return {
            "status": "human_approval_required",
            "approval_packet": packet,
            "observation_plan": None,
            "agents_run": ["synthesizer"],
        }
    return {
        "status": "plan_ready",
        "approval_packet": None,
        "observation_plan": packet,
        "agents_run": ["synthesizer"],
    }


def blocked_node(state: ChangeState) -> ChangeState:
    # Fail closed: an unproven proposal never leaves as an approvable command.
    return {
        "status": "blocked_manual_review",
        "approval_packet": {
            "request": state["request"],
            "evidence": state["citations"],
            "reason": state["reason"],
            "proposed_commands": [],
            "rejected_unsafe_proposals": state["rejected_history"],
            "decision_needed": "승인 권한자가 수동으로 검토",
        },
        "observation_plan": None,
        "agents_run": ["blocked"],
    }


def insufficient_evidence_node(_: ChangeState) -> ChangeState:
    return {
        "status": "insufficient_evidence",
        "approval_packet": None,
        "observation_plan": None,
        "agents_run": ["insufficient_evidence"],
    }


def build_graph():
    graph = StateGraph(ChangeState)
    graph.add_node("planner", planner_node)
    graph.add_node("evidence_reviewer", evidence_reviewer_node)
    graph.add_node("risk_guard", risk_guard_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("blocked", blocked_node)
    graph.add_node("insufficient_evidence", insufficient_evidence_node)
    graph.add_edge(START, "planner")
    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "evidence_reviewer": "evidence_reviewer",
            "insufficient_evidence": "insufficient_evidence",
        },
    )
    graph.add_edge("evidence_reviewer", "risk_guard")
    graph.add_conditional_edges(
        "risk_guard",
        route_after_risk,
        {"planner": "planner", "blocked": "blocked", "synthesizer": "synthesizer"},
    )
    for terminal in ("synthesizer", "blocked", "insufficient_evidence"):
        graph.add_edge(terminal, END)
    return graph.compile()


WORKFLOW = build_graph()


def run_change_review(payload: ChangeRequest) -> dict:
    state = WORKFLOW.invoke(
        {
            **payload.model_dump(),
            "revision_count": 0,
            "agents_run": [],
            "rejected_history": [],
        }
    )
    return {
        "difficulty": 3,
        "mode": "live" if is_live_mode() else "fixture",
        "business_use_case": "it_change_risk_review",
        "workflow_engine": "langgraph",
        "agents_run": state["agents_run"],
        "severity": state["severity"],
        "revision_count": state["revision_count"],
        "max_revisions": MAX_REVISIONS,
        "status": state["status"],
        "citations": state["citations"],
        "retrieval_trace": state.get("retrieval_trace", []),
        "draft": state["draft"],
        "approval_packet": state["approval_packet"],
        "observation_plan": state["observation_plan"],
        # This workflow reviews changes. It never runs one.
        "executed_commands": [],
    }


def create_app() -> FastAPI:
    app = FastAPI(title="Week 3 — LangGraph Change Review", version="3.0.0")

    @app.get("/health")
    def health() -> dict[str, str | int | bool]:
        return {
            "status": "ok",
            "difficulty": 3,
            "workflow_engine": "langgraph",
            "live_mode": is_live_mode(),
        }

    @app.get("/diagnostics")
    def diagnostics(include_chunks: bool = False) -> dict:
        try:
            return collection_diagnostics(
                WEEK_COLLECTIONS["week3"], include_chunks=include_chunks
            )
        except LiveRagError as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "live_rag_unavailable", "message": str(error)},
            ) from error

    @app.post("/review-change")
    def review_change(payload: ChangeRequest) -> dict:
        try:
            return run_change_review(payload)
        except LiveRagError as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "live_rag_unavailable", "message": str(error)},
            ) from error

    return app


app = create_app()
