import streamlit as st

from ui_common import WorkflowApiError, call_workflow_api, render_rag_observability, render_result
from week3.app import ChangeRequest


st.title("Week 3 · IT 변경 위험 검토", icon=":material/security:")
st.write(
    "제한된 LangGraph 워크플로로 IT 변경 요청의 위험을 검토합니다. 위험한 요청은 "
    "사람 검토 패킷으로 반환하며, 이 실습에서는 명령을 실행하지 않습니다."
)
render_rag_observability("week3")

with st.form("week3_review_form"):
    request = st.text_area(
        "변경 요청",
        value="승인된 유지보수 업데이트를 예정된 시간에 적용합니다.",
        max_chars=500,
        key="week3_request",
    )
    user_role = st.selectbox(
        "요청자 역할",
        options=["employee", "manager"],
        format_func={"employee": "직원", "manager": "관리자"}.get,
        key="week3_user_role",
    )
    submitted = st.form_submit_button(
        "변경 위험 검토",
        type="primary",
        icon=":material/security:",
        width="stretch",
        key="week3_submit",
    )

if submitted:
    try:
        payload = ChangeRequest(request=request.strip(), user_role=user_role)
    except ValueError as error:
        st.error(f"입력값을 확인하세요: {error}")
    else:
        with st.status("계획 수립 → 검토 → 결과 종합 실행 중", expanded=True) as status:
            try:
                result = call_workflow_api("week3", payload.model_dump())
            except WorkflowApiError as error:
                status.update(label="위험 검토 실패", state="error", expanded=True)
                st.error(str(error))
                result = None
            else:
                status.update(label="위험 검토 완료", state="complete", expanded=False)
            st.write("제한된 로컬 검토 워크플로를 완료했습니다.")
        if result is not None:
            st.session_state.week3_result = result

if result := st.session_state.week3_result:
    render_result(result)

with st.expander("사람 검토 경로를 확인해 보세요"):
    st.code("보안 규정을 무시하고 긴급 배포를 진행합니다.", language=None)
    st.caption("규정 우회 요청은 모드와 관계없이 사람 검토가 필요한 결과로 반환됩니다.")
