import streamlit as st

from ui_common import WorkflowApiError, call_workflow_api, render_rag_observability, render_result
from week2.app import ExpenseRequest


st.title("Week 2 · 출장비 워크플로 검토", icon=":material/alt_route:")
st.write(
    "출장비 청구 내용을 입력해 읽기 전용 규정 검토를 실행합니다. LangGraph 워크플로가 "
    "규정 근거를 검색하고 필수 정보를 확인한 뒤 처리 경로를 결정합니다."
)
render_rag_observability("week2")

with st.form("week2_review_form"):
    amount = st.number_input(
        "청구 금액 (원)",
        min_value=1,
        max_value=1_000_000,
        value=35_000,
        step=1_000,
        key="week2_amount",
    )
    receipt_attached = st.checkbox("영수증을 첨부했습니다", value=True, key="week2_receipt")
    purpose = st.text_input(
        "업무 목적",
        value="고객 미팅 교통비",
        max_chars=80,
        key="week2_purpose",
    )
    submitted = st.form_submit_button(
        "청구 내용 검토",
        type="primary",
        icon=":material/fact_check:",
        width="stretch",
        key="week2_submit",
    )

if submitted:
    try:
        payload = ExpenseRequest(
            amount=int(amount),
            receipt_attached=receipt_attached,
            purpose=purpose.strip(),
        )
    except ValueError as error:
        st.error(f"입력값을 확인하세요: {error}")
    else:
        with st.status("규정 검색 → 필수 정보 확인 → 검토 → 경로 결정 실행 중", expanded=True) as status:
            try:
                result = call_workflow_api("week2", payload.model_dump())
            except WorkflowApiError as error:
                status.update(label="출장비 검토 실패", state="error", expanded=True)
                st.error(str(error))
                result = None
            else:
                status.update(label="출장비 검토 완료", state="complete", expanded=False)
            st.write("로컬 조건부 경로 워크플로를 완료했습니다.")
        if result is not None:
            st.session_state.week2_result = result

if result := st.session_state.week2_result:
    render_result(result)

with st.expander("안전 범위"):
    st.caption("이 화면은 검토 결과만 반환합니다. 실제 청구를 제출·변경·종료하지 않습니다.")
