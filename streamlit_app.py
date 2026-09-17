import streamlit as st


st.set_page_config(
    page_title="에이전트 워크플로 실습",
    page_icon=":material/account_tree:",
    layout="wide",
)

for result_key in ("week1_result", "week2_result", "week3_result"):
    st.session_state.setdefault(result_key, None)

page = st.navigation(
    [
        st.Page(
            "app_pages/week1.py",
            title="Week 1 · 규정 질의응답",
            icon=":material/menu_book:",
            default=True,
        ),
        st.Page(
            "app_pages/week2.py",
            title="Week 2 · 워크플로 검토",
            icon=":material/alt_route:",
        ),
        st.Page(
            "app_pages/week3.py",
            title="Week 3 · 위험 검토",
            icon=":material/security:",
        ),
    ],
    position="top",
)

with st.sidebar:
    st.subheader("에이전트 워크플로 실습")
    st.caption("Week 1~3 LangChain RAG · LangGraph 실습 화면")
    st.info(
        "이 화면은 로컬 fixture 워크플로를 직접 실행합니다. "
        "실시간 LLM, 데이터베이스, 쓰기 권한 도구는 사용하지 않습니다.",
        icon=":material/info:",
    )

page.run()
