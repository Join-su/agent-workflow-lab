import streamlit as st

from ui_common import WorkflowApiError, call_workflow_api, render_rag_observability, render_result


st.title("Week 1 · HR 규정 RAG 질의응답", icon=":material/menu_book:")
st.write(
    "로컬 HR 휴가 규정에 질문하세요. 워크플로가 근거 문서를 검색하고 답변을 만든 뒤, "
    "출처가 있는지 확인합니다."
)
render_rag_observability("week1")

with st.form("week1_query_form"):
    question = st.text_input(
        "규정 질문",
        value="휴가 신청은 며칠 전에 해야 하나요?",
        max_chars=300,
        key="week1_question",
    )
    submitted = st.form_submit_button(
        "규정 확인 실행",
        type="primary",
        icon=":material/play_arrow:",
        width="stretch",
        key="week1_submit",
    )

if submitted:
    if len(question.strip()) < 3:
        st.error("세 글자 이상의 질문을 입력하세요.")
    else:
        with st.status("문서 검색 → 답변 생성 → 근거 검증 실행 중", expanded=True) as status:
            try:
                result = call_workflow_api("week1", {"question": question.strip()})
            except WorkflowApiError as error:
                status.update(label="규정 확인 실패", state="error", expanded=True)
                st.error(str(error))
                result = None
            else:
                status.update(label="규정 확인 완료", state="complete", expanded=False)
            st.write("로컬 LangGraph 워크플로를 완료했습니다.")
        if result is not None:
            st.session_state.week1_result = result

if result := st.session_state.week1_result:
    render_result(result)

with st.expander("근거 부족 결과를 확인해 보세요"):
    st.code("오늘 점심 메뉴는 무엇인가요?", language=None)
    st.caption("적재된 규정 문서에 없는 질문은 모드와 관계없이 근거 부족으로 종료됩니다.")
