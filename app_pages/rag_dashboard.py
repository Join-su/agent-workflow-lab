import streamlit as st

from ui_common import WorkflowApiError, get_workflow_diagnostics


WEEKS = {
    "week1": "Week 1 · HR 규정",
    "week2": "Week 2 · 출장비",
    "week3": "Week 3 · IT 변경",
}


st.title("RAG 연결 현황", icon=":material/hub:")
st.write(
    "이 화면은 Streamlit이 각 Week FastAPI의 `/diagnostics`를 호출해, "
    "실제 API 연결과 pgvector 문서 청크 상태를 읽기 전용으로 표시합니다."
)

diagnostics: dict[str, dict] = {}
unavailable: dict[str, str] = {}
for week in WEEKS:
    try:
        diagnostics[week] = get_workflow_diagnostics(week, include_chunks=True)
    except WorkflowApiError as error:
        unavailable[week] = str(error)

with st.container(border=True):
    st.subheader("API · Vector DB 연결 상태", icon=":material/lan:")
    cards = st.columns(3)
    for card, (week, label) in zip(cards, WEEKS.items(), strict=True):
        with card:
            data = diagnostics.get(week)
            if data is None:
                st.metric(label, "API 미연결", border=True)
                st.caption("해당 FastAPI 서버를 실행하세요.")
            elif data.get("mode") != "live":
                st.metric(label, "FIXTURE", border=True)
                st.caption("`--env-file .env`로 재시작이 필요합니다.")
            else:
                st.metric(label, "LIVE", f"청크 {data['chunk_count']}개", border=True)
                st.caption(f"키 {data['api_key_prefix']} · {data['collection']}")

if unavailable:
    st.warning(
        "연결되지 않은 API: " + ", ".join(WEEKS[week] for week in unavailable),
        icon=":material/link_off:",
    )

selected_week = st.segmented_control(
    "상세 확인 대상",
    options=list(WEEKS),
    default="week1",
    format_func=WEEKS.get,
    key="rag_dashboard_selected_week",
)
selected = diagnostics.get(selected_week)

if selected is None:
    st.info("선택한 Week API를 시작하면 연결 경로와 저장 청크를 표시합니다.")
elif selected.get("mode") != "live":
    st.error(
        "선택한 API가 fixture 모드입니다. `--env-file .env` 옵션으로 재시작하세요.",
        icon=":material/error:",
    )
else:
    with st.container(border=True):
        st.subheader(f"{WEEKS[selected_week]} Retriever 경로", icon=":material/account_tree:")
        with st.status("live RAG 연결 확인 완료", state="complete", expanded=True):
            st.write(f"1. FastAPI가 키 식별자 `{selected['api_key_prefix']}`로 OpenAI API를 사용합니다.")
            st.write(f"2. `{selected['embedding_model']}`이 질문을 벡터로 변환합니다.")
            st.write(
                f"3. pgvector `{selected['collection']}`에서 유사도 {selected['min_relevance']} 이상을 검색합니다."
            )
            st.write("4. 선택된 청크만 LangGraph 워크플로와 LLM 답변의 근거로 전달됩니다.")

    with st.container(border=True):
        st.subheader("pgvector에 저장된 문서 청크", icon=":material/database:")
        chunks = selected.get("chunks", [])
        st.dataframe(
            [
                {
                    "문서 ID": chunk["document_id"],
                    "청크 ID": chunk["chunk_id"],
                    "원본 문서": chunk["source"],
                    "문자 수": chunk["characters"],
                    "벡터 차원": chunk["embedding_dimensions"],
                }
                for chunk in chunks
            ],
            hide_index=True,
            key="rag_dashboard_chunks",
        )
        for chunk in chunks:
            with st.expander(f"{chunk['chunk_id']} · 저장된 본문 확인"):
                st.code(chunk["content_preview"], language="markdown")
        st.caption("임베딩 벡터 전문, 전체 API 키, DB 연결 문자열은 표시하지 않습니다.")
