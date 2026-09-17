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
            "app_pages/rag_dashboard.py",
            title="RAG 연결 현황",
            icon=":material/hub:",
            default=True,
        ),
        st.Page(
            "app_pages/week1.py",
            title="Week 1 · 규정 질의응답",
            icon=":material/menu_book:",
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
    st.caption("OpenAI · pgvector · LangGraph 실습")
    st.info(
        "먼저 RAG 연결 현황에서 API · 문서 청크 · Retriever 상태를 확인한 뒤 "
        "Week별 실습을 실행하세요.",
        icon=":material/info:",
    )

page.run()
