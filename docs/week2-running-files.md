# Week 2: 실제 실행 파일과 역할

## 이 Week의 한 줄 목표

출장비 요청의 업무 목적과 영수증 여부를 확인하고, 출장비 규정을 찾아 다음 처리 경로를 결정합니다.

## 최소 실행 명령

```powershell
# DB가 아직 꺼져 있다면
docker compose --env-file .env -f infra/compose.pgvector.yml up -d

# Week 2 문서 적재
.\.venv\Scripts\python.exe -m shared.ingest --week week2

# Week 2 백엔드
.\.venv\Scripts\uvicorn.exe --env-file .env week2.app:app --port 8012

# UI는 한 번만 실행하면 Week 1~3을 모두 사용한다
.\.venv\Scripts\streamlit.exe run streamlit_app.py
```

## 실제로 움직이는 파일

| 파일 | 언제 움직이나 | 역할 |
|---|---|---|
| `.env` | DB·적재기·백엔드 실행 시 | live RAG 설정과 비밀값을 제공한다. |
| `infra/compose.pgvector.yml` | DB 기동 시 | Docker 안의 PostgreSQL+pgvector를 실행한다. |
| `knowledge/week2/expense-policy.md` | 적재 시 | 출장비 규정 원문이다. |
| `knowledge/week2/expense-evidence-guide.md` | 적재 시 | 영수증 등 증빙 기준 원문이다. |
| `shared/ingest.py` | 적재 시 | Week 2 문서를 청크·임베딩으로 바꿔 `agent_workflow_week2`에 저장한다. |
| `shared/live_rag.py` | 적재·검색 시 | OpenAI와 pgvector를 쓰는 공용 코드다. |
| `week2/app.py` | 백엔드 실행 시 | `POST /review`를 제공한다. 규정 검색, 증빙 확인, 다음 경로 결정을 한다. |
| `streamlit_app.py` | UI 실행 시 | 모든 Week 화면의 메뉴 시작점이다. |
| `app_pages/week2.py` | Week 2 탭 선택 시 | 금액·영수증·업무 목적을 입력받아 Week 2 API를 호출한다. |
| `ui_common.py` | UI 실행 시 | 공통 HTTP 통신과 결과 표시를 담당한다. |

## Week 2에서 DB가 하는 일

DB는 “영수증이 없으면 보완 요청” 같은 규정 문장들을 보관합니다. `week2/app.py`가 업무 목적과 비슷한 규정 청크를 찾고, 영수증 체크박스 값은 별도로 확인합니다. 그래서 DB는 규정을 찾는 역할, FastAPI는 규정과 입력값을 함께 판단하는 역할을 합니다.

`app_pages/rag_dashboard.py`는 실습의 필수 경로가 아니라 저장 상태를 확인하는 보조 화면입니다.
