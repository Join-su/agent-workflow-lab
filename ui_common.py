from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st


class WorkflowApiError(RuntimeError):
    """Raised when the Streamlit frontend cannot obtain a workflow result."""


API_TARGETS = {
    "week1": ("WEEK1_API_URL", "http://127.0.0.1:8011/query"),
    "week2": ("WEEK2_API_URL", "http://127.0.0.1:8012/review"),
    "week3": ("WEEK3_API_URL", "http://127.0.0.1:8013/review-change"),
}


def call_workflow_api(week: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Call a weekly FastAPI service without exposing server internals to the UI."""
    environment_key, default_url = API_TARGETS[week]
    url = os.getenv(environment_key, default_url)
    try:
        response = httpx.post(url, json=payload, timeout=30.0)
    except httpx.RequestError as error:
        raise WorkflowApiError(
            "워크플로 API에 연결할 수 없습니다. 해당 FastAPI 서버가 실행 중인지 확인하세요."
        ) from error
    if response.is_error:
        try:
            detail = response.json().get("detail", {})
            message = detail.get("message") if isinstance(detail, dict) else str(detail)
        except ValueError:
            message = response.text
        raise WorkflowApiError(message or f"워크플로 API 요청이 실패했습니다. (HTTP {response.status_code})")
    return response.json()


SUCCESS_STATUSES = {"answered", "approved_for_next_step", "done"}
REVIEW_STATUSES = {"human_review", "blocked_manual_review"}
STATUS_LABELS = {
    "answered": "답변 완료",
    "approved_for_next_step": "다음 단계 진행 가능",
    "done": "검토 완료",
    "insufficient_evidence": "근거 부족",
    "human_review": "사람 검토 필요",
    "blocked_manual_review": "수동 검토로 중단",
    "unknown": "알 수 없음",
}
USE_CASE_LABELS = {
    "hr_leave_policy_self_service": "HR 휴가 규정 질의응답",
    "expense_claim_precheck": "출장비 청구 사전 검토",
    "it_change_risk_review": "IT 변경 위험 검토",
}
NODE_LABELS = {
    "retriever": "문서 검색",
    "answer": "답변 생성",
    "evidence_guard": "근거 검증",
    "policy_retriever": "규정 검색",
    "evidence_extractor": "필수 정보 확인",
    "policy_reviewer": "규정 검토",
    "risk_router": "경로 결정",
    "planner": "계획 수립",
    "evidence_reviewer": "근거 검토",
    "risk_reviewer": "위험 검토",
    "synthesizer": "결과 종합",
    "insufficient_evidence": "근거 부족 종료",
}
FOLLOW_UP_LABELS = {"receipt_required": "영수증 첨부 필요"}
REASON_LABELS = {"policy_bypass_requested": "규정 우회 요청 감지"}


def render_result(result: dict[str, Any]) -> None:
    """Render the common, safe-to-display parts of a workflow result."""
    status = result.get("status", "unknown")
    status_label = STATUS_LABELS.get(status, str(status))
    citations = [
        {
            "문서 ID": citation.get("document_id", ""),
            "문서 조각 ID": citation.get("chunk_id", ""),
        }
        for citation in result.get("citations", [])
    ]
    human_review_packet = result.get("human_review_packet")
    review_details = None
    if human_review_packet:
        review_details = {
            "요청 내용": human_review_packet.get("request"),
            "근거": citations,
            "검토 사유": REASON_LABELS.get(
                human_review_packet.get("reason"), human_review_packet.get("reason")
            ),
            "결정이 필요한 사항": human_review_packet.get("decision_needed"),
        }

    with st.container(border=True):
        st.subheader("워크플로 결과")
        if status in SUCCESS_STATUSES:
            st.success("허용된 처리 경로를 정상적으로 완료했습니다.", icon=":material/check_circle:")
        elif status in REVIEW_STATUSES:
            st.warning(
                "사람의 검토가 필요해 처리하지 않았습니다. 명령은 실행되지 않았습니다.",
                icon=":material/person_alert:",
            )
        else:
            st.info(
                "계속 처리할 근거가 부족해 워크플로를 종료했습니다.",
                icon=":material/info:",
            )

        metadata, trace = st.columns(2, vertical_alignment="top")
        with metadata:
            st.metric("처리 상태", status_label)
            st.caption(
                f"업무 시나리오: {USE_CASE_LABELS.get(result.get('business_use_case'), '알 수 없음')}"
            )
            st.caption("워크플로 엔진: LangGraph")
        with trace:
            st.markdown("**실행 단계**")
            st.code(
                " → ".join(
                    NODE_LABELS.get(node, node) for node in result.get("agents_run", [])
                )
                or "실행 기록 없음",
                language=None,
            )

        if answer := result.get("answer"):
            st.markdown("**답변**")
            st.info(answer, icon=":material/chat:")

        if review_summary := result.get("review_summary"):
            st.markdown("**검토 요약**")
            st.info(review_summary, icon=":material/fact_check:")

        if draft := result.get("draft"):
            st.markdown("**검토 초안**")
            st.info(draft, icon=":material/edit_note:")

        if citations:
            st.markdown("**근거 문서**")
            st.dataframe(citations, hide_index=True)

        details = {
            "처리 상태": status_label,
            "답변": result.get("answer"),
            "검토 요약": result.get("review_summary"),
            "검토 초안": result.get("draft"),
            "추가 확인 필요": FOLLOW_UP_LABELS.get(
                result.get("required_follow_up"), result.get("required_follow_up")
            ),
            "수정 횟수": result.get("revision_count"),
            "근거 문서": citations,
            "사람 검토 내용": review_details,
        }
        with st.expander("상세 결과 보기"):
            st.json({key: value for key, value in details.items() if value is not None}, expanded=2)
