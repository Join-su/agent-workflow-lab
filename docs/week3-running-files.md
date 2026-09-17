# Week 3: 실제 실행 파일과 역할

## 이 Week의 한 줄 목표

IT 변경 요청과 보안 규정을 함께 살펴보고, 위험한 우회 요청은 자동 실행하지 않고 사람 검토로 보냅니다.

## 최소 실행 명령

```powershell
# DB가 아직 꺼져 있다면
docker compose --env-file .env -f infra/compose.pgvector.yml up -d

# Week 3 문서 적재
.\.venv\Scripts\python.exe -m shared.ingest --week week3

# Week 3 백엔드
.\.venv\Scripts\uvicorn.exe --env-file .env week3.app:app --port 8013

# UI는 한 번만 실행하면 Week 1~3을 모두 사용한다
.\.venv\Scripts\streamlit.exe run streamlit_app.py
```

## 실제로 움직이는 파일

| 파일 | 언제 움직이나 | 역할 |
|---|---|---|
| `.env` | DB·적재기·백엔드 실행 시 | live RAG 설정을 제공한다. |
| `infra/compose.pgvector.yml` | DB 기동 시 | pgvector가 포함된 PostgreSQL 컨테이너를 실행한다. |
| `knowledge/week3/security-policy.md` | 적재 시 | 보안·변경 규정 원문이다. |
| `knowledge/week3/change-request-template.md` | 적재 시 | 변경 요청에 필요한 정보 원문이다. |
| `shared/ingest.py` | 적재 시 | Week 3 문서를 청크·임베딩으로 바꿔 `agent_workflow_week3`에 저장한다. |
| `shared/live_rag.py` | 적재·검색 시 | OpenAI 임베딩, pgvector 검색, 근거 기반 답변 생성을 제공한다. |
| `week3/app.py` | 백엔드 실행 시 | `POST /review-change`를 제공한다. 변경 계획·근거·위험 검토를 LangGraph로 실행한다. |
| `streamlit_app.py` | UI 실행 시 | 메뉴와 공통 세션 상태를 만든다. |
| `app_pages/week3.py` | Week 3 탭 선택 시 | 변경 요청과 역할을 입력받아 Week 3 API를 호출한다. |
| `ui_common.py` | UI 실행 시 | 공통 API 호출, 결과 카드, 출처 표시를 맡는다. |

## 안전장치

`week3/app.py`는 문서를 찾는 것에서 끝나지 않습니다. “규정 무시”, “우회”, “긴급 배포” 같은 요청은 실제 명령을 실행하지 않고 `human_review` 결과로 멈춥니다. 즉 DB는 판단 근거를 찾고, 백엔드는 안전한 경로를 선택하며, UI는 그 결과를 보여 줍니다.

`app_pages/rag_dashboard.py`는 저장 청크와 연결 상태를 보는 보조 화면입니다.
