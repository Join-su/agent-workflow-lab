# Week 1 — HR 규정 근거 기반 Q&A (난이도 1/5)

## 프로젝트 결과

구성원이 합성 휴가 규정을 질문하면 관련 chunk를 검색하고, 근거가 있을 때만 답변·citation을 반환합니다. 근거가 없으면 `insufficient_evidence`로 종료하며 휴가를 신청하거나 승인하지 않습니다.

```text
question → retrieve → answer → grounding_guard → answered | insufficient_evidence
```

## 이번 주에 처음 배우는 것

- Pydantic `QueryRequest`와 FastAPI 입력 경계
- LangChain `Document`·metadata·`RecursiveCharacterTextSplitter`
- fixture retrieval과 live `OpenAIEmbeddings`·`PGVector` 계약
- citation과 grounded generation
- `QueryState`, node, edge, 선형 `StateGraph`
- dependency injection, `TestClient`, 성공/실패 계약 테스트

## 아직 다루지 않는 것

structured output 분류, metadata category filter, conditional edge, 멀티에이전트 loop, 사람 승인 packet은 Week 2·3에서 다룹니다.

## 핵심 코드

- `POLICY_SOURCE_DOCUMENTS`: 분할 전 합성 규정
- `split_policy_documents()`: 검색 chunk와 `chunk_id` 생성
- `PolicyServices`: fixture/live 구현이 공유하는 의존성 경계
- `QueryState`: graph가 전달하는 상태
- `build_workflow()`: 선형 graph compile
- `run_policy_query()`: API·테스트·Notebook의 canonical 진입점

## Notebook 순서

1. `01_request_response_models.ipynb` — Pydantic·FastAPI 요청 경계
2. `02_documents_and_splitting.ipynb` — `Document`와 splitter
3. `03_embeddings_pgvector_retrieval.ipynb` — embedding·pgvector·검색 계약
4. `04_linear_stategraph.ipynb` — state·node·edge·trace
5. `05_grounded_api_testing.ipynb` — citation·미지원 질문·HTTP 통합 테스트

각 Notebook은 하나의 작은 시나리오만 다루며 `app.py` 구현을 복제하지 않습니다.

## 실행·완료 기준

```bash
.venv/bin/python -m unittest week1.tests.test_policy_qa -v
APP_MODE=fixture .venv/bin/uvicorn week1.app:app --port 8011
curl -s -X POST http://127.0.0.1:8011/query \
  -H 'content-type: application/json' \
  -d '{"question":"How early should I request vacation?"}'
```

완료 기준:

- 지원 질문은 근거와 citation을 반환한다.
- 미지원 질문은 답변을 만들지 않는다.
- splitter 결과에는 안정적인 `chunk_id`가 있다.
- API 422, graph trace, fixture/live mode 경계를 설명할 수 있다.
- 5개 Notebook이 위에서 아래로 실행된다.

Week 2는 이 기초를 반복 설명하지 않고 structured classification·filtered retrieval·conditional routing부터 시작합니다.
