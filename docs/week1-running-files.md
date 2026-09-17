# Week 1: 실제 실행 파일과 역할

## 이 Week의 한 줄 목표

휴가 규정 질문을 받으면 pgvector에서 휴가 문서 조각을 찾고, 그 조각을 근거로 답합니다.

## 최소 실행 명령

```powershell
# 1. DB 기동 (처음 한 번 또는 DB가 꺼졌을 때)
docker compose --env-file .env -f infra/compose.pgvector.yml up -d

# 2. Week 1 문서 적재 (문서가 바뀌었을 때)
.\.venv\Scripts\python.exe -m shared.ingest --week week1

# 3. Week 1 백엔드
.\.venv\Scripts\uvicorn.exe --env-file .env week1.app:app --port 8011

# 4. 별도 터미널: UI
.\.venv\Scripts\streamlit.exe run streamlit_app.py
```

`/health`에서 `live_mode: true`이면 3번 백엔드가 `.env`를 읽고 있습니다.

## 실제로 움직이는 파일

| 파일 | 언제 움직이나 | 역할 |
|---|---|---|
| `.env` | 1~3번 실행 시 | API 키, `APP_MODE`, DB 접속 정보를 제공한다. Git에 넣지 않는다. |
| `infra/compose.pgvector.yml` | 1번 | Docker에게 PostgreSQL+pgvector 컨테이너를 만들고 5432 포트로 열라고 알려 준다. |
| `knowledge/week1/leave-policy.md` | 2번 | 휴가 규정 원문이다. |
| `knowledge/week1/leave-handover-checklist.md` | 2번 | 휴가 인수인계 원문이다. |
| `shared/ingest.py` | 2번 | Markdown을 작은 청크로 나누고 OpenAI 임베딩을 만든 뒤 DB에 저장한다. |
| `shared/live_rag.py` | 2번, 3번 | OpenAI 임베딩·채팅과 pgvector 검색을 연결하는 공용 도구다. |
| `week1/app.py` | 3번 | `POST /query`를 제공한다. Retriever → 답변 생성 → 근거 확인 LangGraph를 실행한다. |
| `streamlit_app.py` | 4번 | Streamlit의 메뉴와 공통 화면 시작점이다. |
| `app_pages/week1.py` | 4번, Week 1 탭 선택 시 | 휴가 질문 입력 폼을 보여 주고 Week 1 API에 HTTP 요청한다. |
| `ui_common.py` | 4번 | UI의 공통 결과 카드, HTTP 호출, 출처·Retriever 표시 기능이다. |

## 질문 한 번의 여행

```text
"휴가는 언제 신청하나요?"
        │
app_pages/week1.py (입력 화면)
        │ HTTP POST /query
week1/app.py (Retriever)
        │ OpenAI로 질문 임베딩
pgvector의 agent_workflow_week1 테이블
        │ 비슷한 leave-policy 청크 반환
week1/app.py (OpenAI 답변 생성)
        │ 답변 + citations
ui_common.py / app_pages/week1.py (화면 표시)
```

`app_pages/rag_dashboard.py`는 청크와 연결 상태를 보여 주는 **보조 관측 화면**입니다. Week 1 질문·검색·답변의 필수 파일은 아닙니다.
