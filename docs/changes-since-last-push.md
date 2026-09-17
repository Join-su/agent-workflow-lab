# 마지막 push 이후 작업 정리

기준 커밋: `a5f0a07` (`add env ex`)

이 문서는 위 커밋 이후 작업 폴더에 남아 있는 **미커밋 변경 사항**을 정리한다. 아직 새 변경을 원격 저장소에 push하지 않았다.

## 1. Week 1~3 통합 Streamlit 화면

- `streamlit_app.py`, `app_pages/week1.py`, `app_pages/week2.py`, `app_pages/week3.py`, `ui_common.py`를 추가했다.
- 단일 Streamlit 앱에서 Week 1~3 학습 시나리오를 전환하고, 입력 폼·처리 상태·workflow trace·citation·사람 검토 결과를 표시한다.
- UI는 workflow 함수를 Python으로 직접 호출하지 않는다. 각 Week FastAPI API를 HTTP로 호출한다.
  - Week 1: 기본 `http://127.0.0.1:8011/query`
  - Week 2: 기본 `http://127.0.0.1:8012/review`
  - Week 3: 기본 `http://127.0.0.1:8013/review-change`
- 배포 환경에서는 `WEEK1_API_URL`, `WEEK2_API_URL`, `WEEK3_API_URL`로 대상 API 주소를 바꿀 수 있다.
- API 연결·응답 오류는 UI에서 사용자에게 표시한다.

## 2. OpenAI + pgvector Live RAG

- 기본 `APP_MODE=fixture`는 기존과 동일하게 API 키·DB 없이 동작한다.
- `APP_MODE=live`일 때만 `shared/live_rag.py`가 OpenAI 임베딩·채팅 모델과 PostgreSQL/pgvector를 사용한다.
- `langchain-postgres`의 권장 API인 `PGEngine`과 `PGVectorStore`를 사용한다.
- 주차별 검색 table은 다음처럼 분리된다.
  - `agent_workflow_week1`
  - `agent_workflow_week2`
  - `agent_workflow_week3`
- 검색 결과가 최소 관련도 기준을 충족하지 않으면 모델을 호출하지 않고 `insufficient_evidence`로 종료한다.
- citation은 LLM이 생성하지 않는다. 실제 검색된 문서의 `document_id`, `chunk_id` 메타데이터에서 서버가 만든다.
- live 설정·DB·OpenAI 오류는 FastAPI에서 `503`과 `live_rag_unavailable` 코드로 반환한다. 비밀값은 응답이나 로그에 포함하지 않는다.

### Week별 적용 범위

| Week | live 검색 | OpenAI 생성 | 안전 규칙 |
|---|---|---|---|
| 1 | HR 휴가 규정 | 근거 기반 답변 | 근거가 없으면 답변하지 않음 |
| 2 | 출장비 규정 | 검토 근거 요약 | 영수증 누락 판단은 결정론적 규칙 유지 |
| 3 | IT 보안 변경 규정 | 근거 기반 검토 초안 | 정책 우회 요청은 계속 사람 검토로 전환 |

## 3. 문서 적재와 Docker 환경

- `infra/compose.pgvector.yml`에 로컬 전용 `127.0.0.1:5432` PostgreSQL + pgvector 서비스를 추가했다.
- `knowledge/week1`~`knowledge/week3`에 NoriWorks 가상 기업의 휴가·출장비·IT 변경 운영 정책 Markdown 원본을 추가했다. 문서가 실습용 가상 정책임을 `knowledge/README.md`에 명시했다.
- `python -m shared.ingest --week week1` 형식의 적재 CLI를 추가했다.
  - Markdown을 분할하고, OpenAI 임베딩을 생성하고, 주차별 table에 upsert한다.
  - 청크 ID는 안정적으로 생성되어 일반 재적재 시 같은 문서를 갱신한다.
  - `--reset`은 해당 주차 table과 적재 문서를 삭제하고 다시 만들므로, 임베딩 모델/차원 변경 등 의도적인 초기화 때만 사용한다.
- `.env.example`에 live 실행용 환경 변수를 추가했다.
  - `OPENAI_API_KEY`, `OPENAI_MODEL`
  - `OPENAI_EMBEDDING_MODEL`, `OPENAI_EMBEDDING_DIMENSIONS`
  - `DATABASE_URL`, `POSTGRES_PASSWORD`
  - `RAG_RETRIEVAL_K`, `RAG_MIN_RELEVANCE`

## 4. API·의존성·문서 보완

- Week 1 API에 브라우저용 `/` 안내와 `/favicon.ico` 응답을 추가했다.
- `langchain-openai`, `langchain-postgres`, `psycopg[binary]`, Streamlit 의존성을 추가하고 `uv.lock`을 갱신했다.
- `pyproject.toml`의 개발 의존성을 `httpx`, `jupyter` 기준으로 정리했다.
- Windows 실행 절차와 Live RAG 설정 절차를 README 및 `docs/docker-pgvector-live-rag-setup.md`에 반영했다.
- Notebook 검사에서 파일을 UTF-8로 읽도록 보완했다.

## 5. 테스트 및 검증

추가한 테스트:

- `tests/test_streamlit_app.py`: Streamlit `AppTest`로 Week 1~3 화면과 HTTP 호출 경계를 검증한다.
- `tests/test_live_rag.py`: live 환경 변수 검증, 근거 기반 생성, 근거 부족 안전 종료, FastAPI 503 응답을 검증한다.
- `tests/test_ingest.py`: Week별 Markdown 원본과 citation 메타데이터를 검증한다.

마지막 실행 결과:

```text
python -m unittest discover -s . -p "test_*.py" -v

Ran 18 tests
OK
```

추가로 `uv lock`, `uv sync`, Python 컴파일 검사와 Docker Compose 구성 파싱을 완료했다.

## 6. 실제 live 실행 전 남은 환경 준비

구현 및 fixture 테스트는 완료됐지만, 실제 외부 서비스를 사용하는 smoke test는 아직 실행하지 않았다. 다음 준비가 필요하다.

1. `.env`에 유효한 OpenAI API 키와 PostgreSQL 비밀번호를 설정한다.
2. pgvector 컨테이너를 시작한다.
3. Week별 Markdown 문서를 적재한다.
4. 필요한 Week FastAPI 서버를 시작한 뒤 Streamlit을 실행한다.

```powershell
docker compose --env-file .env -f infra/compose.pgvector.yml up -d
.\.venv\Scripts\python.exe -m shared.ingest --week week1
.\.venv\Scripts\uvicorn.exe week1.app:app --port 8011
.\.venv\Scripts\streamlit.exe run streamlit_app.py
```

## 7. 정책 문서 실습 품질 보강

초기 `knowledge` 문서가 한 줄짜리 placeholder여서 RAG 실습에 적합하지 않다는 피드백을 반영했다.

- `knowledge/README.md`에 문서가 가상 기업 **NoriWorks**의 실습용 정책이며 실제 업무·법률 판단에 사용하면 안 된다는 범위를 명시했다.
- 각 Week를 단일 문서가 아닌 두 개의 상호 보완적인 운영 문서로 확장했다.
  - Week 1: 휴가 신청 정책, 휴가 인수인계 체크리스트
  - Week 2: 국내 출장비 사전 검토 정책, 출장비 증빙 안내
  - Week 3: IT 변경·보안 예외 정책, 변경 요청 작성 가이드
- 문서의 규칙과 workflow를 맞췄다.
  - Week 1 fixture도 `영업일 3일 전` 및 인수인계 요구 사항과 일치시켰다.
  - Week 2는 영수증 미첨부 시 `receipt_required` 보완 요청을 유지하고, 지급·세무 판단을 하지 않는다.
  - Week 3는 `무시`, `우회`, `예외`, `긴급 배포`, `긴급 권한` 요청을 `human_review`로 전환한다.
- Markdown 적재 테스트가 각 Week의 두 원본 문서와 citation 메타데이터를 확인하도록 확장했다.
- 이 보강 뒤 전체 테스트는 **19개 통과**했다.
