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


def _workflow_api_url(week: str) -> str:
    environment_key, default_url = API_TARGETS[week]
    return os.getenv(environment_key, default_url)


def call_workflow_api(week: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Call a weekly FastAPI service without exposing server internals to the UI."""
    url = _workflow_api_url(week)
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


def get_workflow_diagnostics(week: str, *, include_chunks: bool = False) -> dict[str, Any]:
    """Read the API's safe live-RAG diagnostics, never local .env or DB directly."""
    endpoint = _workflow_api_url(week).rsplit("/", 1)[0] + "/diagnostics"
    try:
        response = httpx.get(endpoint, params={"include_chunks": include_chunks}, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise WorkflowApiError("RAG 연결 정보를 API에서 읽을 수 없습니다. 서버 상태를 확인하세요.") from error
    return response.json()


def render_rag_observability(week: str) -> None:
    """Show verifiable API → pgvector connection data for one weekly page."""
    with st.container(border=True):
        st.subheader("Live RAG 연결 확인", icon=":material/hub:")
        try:
            diagnostics = get_workflow_diagnostics(week)
        except WorkflowApiError as error:
            st.warning(str(error), icon=":material/link_off:")
            return

        if diagnostics.get("mode") != "live":
            st.info("현재 API는 fixture 모드입니다. live RAG 연결 정보는 표시되지 않습니다.")
            return

        metrics = st.columns(3)
        metrics[0].metric("API 키", diagnostics.get("api_key_prefix", "없음"))
        metrics[1].metric("저장 청크", diagnostics.get("chunk_count", 0))
        metrics[2].metric("유사도 임계값", diagnostics.get("min_relevance", "-"))
        st.caption(
            "API → OpenAI Embeddings → pgvector → Retriever 경로가 연결되었습니다. "
            f"컬렉션: {diagnostics.get('collection')} · "
            f"임베딩 모델: {diagnostics.get('embedding_model')}"
        )

        show_chunks = st.toggle(
            "DB에 저장된 문서 청크 보기",
            key=f"{week}_show_vector_chunks",
            help="청크 본문과 메타데이터만 표시합니다. 임베딩 벡터 전문은 노출하지 않습니다.",
        )
        if show_chunks:
            try:
                details = get_workflow_diagnostics(week, include_chunks=True)
            except WorkflowApiError as error:
                st.error(str(error))
                return
            chunks = details.get("chunks", [])
            st.dataframe(
                [
                    {
                        "문서 ID": chunk["document_id"],
                        "청크 ID": chunk["chunk_id"],
                        "원본": chunk["source"],
                        "문자 수": chunk["characters"],
                        "벡터 차원": chunk["embedding_dimensions"],
                    }
                    for chunk in chunks
                ],
                hide_index=True,
                key=f"{week}_vector_chunk_table",
            )
            for chunk in chunks:
                with st.expander(f"{chunk['chunk_id']} 본문 미리보기"):
                    st.code(chunk["content_preview"], language="markdown")


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
            st.caption(f"실행 모드: {result.get('mode', '알 수 없음')}")
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

        retrieval_trace = result.get("retrieval_trace", [])
        if retrieval_trace:
            with st.status("RAG Retriever 실행 기록", state="complete", expanded=False):
                st.write("질문을 OpenAI 임베딩으로 변환한 뒤 pgvector 유사도 검색을 실행했습니다.")
                st.write("임계값을 통과한 청크만 LLM 답변의 근거로 전달했습니다.")
            st.dataframe(
                [
                    {
                        "문서 ID": item["document_id"],
                        "청크 ID": item["chunk_id"],
                        "유사도": item["relevance_score"],
                        "근거 사용": "사용" if item["selected"] else "제외",
                    }
                    for item in retrieval_trace
                ],
                hide_index=True,
                key="retrieval_trace_table",
            )

        details = {
            "처리 상태": status_label,
            "실행 모드": result.get("mode"),
            "답변": result.get("answer"),
            "검토 요약": result.get("review_summary"),
            "검토 초안": result.get("draft"),
            "추가 확인 필요": FOLLOW_UP_LABELS.get(
                result.get("required_follow_up"), result.get("required_follow_up")
            ),
            "수정 횟수": result.get("revision_count"),
            "근거 문서": citations,
            "Retriever 실행 기록": retrieval_trace,
            "사람 검토 내용": review_details,
        }
        with st.expander("상세 결과 보기"):
            st.json({key: value for key, value in details.items() if value is not None}, expanded=2)
