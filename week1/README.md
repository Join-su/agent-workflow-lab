# Week 1 — 규정 Q&A (난이도 1/5)

> **목표:** RAG 기반 답변이 “답을 만든다”보다 먼저, *근거가 있을 때만 답하고 인용을 반환하며 근거가 없으면 멈춘다*는 최소 신뢰성 계약을 익힙니다.

이 폴더만 열면 해당 주의 **완성 코드·테스트·Notebook·Docker 배포 파일**을 모두 볼 수 있습니다.

```text
week1/
├── app.py                 # 완성된 FastAPI + fixture RAG + 2단계 Agent 흐름
├── tests/test_api.py      # 핵심 동작 자동 테스트
├── notebooks/             # FastAPI → RAG → Agent → Deployment 실습
├── deploy/                # Dockerfile, compose.yaml
└── README.md              # 난이도·실행·완료 기준
```

## 왜 난이도 1/5인가

이 주는 멀티 에이전트의 수를 늘리지 않습니다. `Retriever → Answer`라는 **직선 흐름**만으로 다음의 가장 작은 계약을 고정합니다.

1. 질문을 HTTP 요청으로 검증한다.
2. fixture 문서에서 관련 근거를 찾는다.
3. 근거가 있으면 답과 `document_id`·`chunk_id` citation을 함께 반환한다.
4. 근거가 없으면 추측하지 않고 `insufficient_evidence`로 종료한다.

즉, 복잡한 planner·분기·재시도·권한 판단을 의도적으로 제외했습니다. 이후 단계가 안정적으로 작동하려면 먼저 **입력 검증 → 검색 → 근거 있는 출력 또는 안전한 종료**가 재현 가능해야 하기 때문입니다.

## Agent 흐름과 결과 계약

```text
Retriever → Answer
```

| 상황 | 핵심 출력 |
|---|---|
| 관련 규정이 있음 | `status: answered`, `answer`, `citations` |
| 관련 규정이 없음 | `status: insufficient_evidence`, 빈 `citations`, `reason: no_matching_policy` |

## 이 주에 반드시 알아야 하는 개념

- **FastAPI endpoint:** `POST /query`, `GET /health`
- **Pydantic 입력 검증:** 질문 길이를 요청 경계에서 제한
- **fixture 기반 retrieval:** 실제 벡터 DB 이전에 검색 입력·출력 계약을 고정
- **citation contract:** 답변의 근거 문서와 chunk 식별자를 반환
- **안전한 실패:** 모르면 채우지 않고 `insufficient_evidence`로 종료
- **결정론적 테스트:** 외부 LLM/API key 없이 같은 입력에는 같은 결과를 검증

현재 구현은 학습과 회귀 테스트를 위한 **fixture 기반 결정론적 RAG**입니다. embedding, vector DB, live LLM은 아직 연결하지 않았습니다.

## 먼저 완성 코드를 실행

저장소 루트에서 실행합니다.

```bash
uv sync
.venv/bin/uvicorn week1.app:app --port 8011
```

다른 터미널에서 확인합니다.

```bash
curl -X POST http://127.0.0.1:8011/query \
  -H 'content-type: application/json' \
  -d '{"question":"휴가 신청은 며칠 전에 해야 하나요?"}'
```

자동 테스트:

```bash
.venv/bin/python -m unittest week1.tests.test_api -v
```

## Notebook 실습 순서

완성 코드의 동작을 확인한 뒤, 아래 순서로 분해해서 실습합니다.

1. `notebooks/01_fastapi.ipynb` — 요청/응답과 validation
2. `notebooks/02_rag.ipynb` — 문서, retrieval, citation
3. `notebooks/03_agents.ipynb` — Retriever/Answer 역할과 안전한 종료
4. `notebooks/04_deployment.ipynb` — Docker artifact와 실행 경계

## Week 2로 넘어가기 전 준비

Week 2에서는 한 줄짜리 답변 흐름에 **정책 검토와 조건 분기**가 추가됩니다. 아래가 유지되어야 다음 Agent가 안정적으로 입력을 소비할 수 있습니다.

- `citations`의 문서·chunk 식별자를 항상 반환한다.
- 정상 답변뿐 아니라 근거 부족 상태도 명시적인 schema로 반환한다.
- 함수 하나가 문서 검색, 답변 생성, 위험 결정을 모두 맡지 않도록 역할 경계를 유지한다.

## 완료 기준

- [ ] 지원되는 질문이 `answered`와 citation을 반환한다.
- [ ] 근거 없는 질문이 추측 없이 `insufficient_evidence`로 끝난다.
- [ ] `week1.tests.test_api`가 통과한다.
- [ ] 완성 코드를 먼저 실행한 뒤 4개 Notebook을 순서대로 실습했다.

## Docker Compose

```bash
cp .env.example .env
cd week1/deploy
docker compose -f compose.yaml up --build
```

Compose artifact는 제공하지만, 현재 서버에는 Docker Compose plugin이 없어 실제 Compose build·기동은 검증하지 못했습니다. 별도 Docker Compose 환경에서 smoke test가 필요합니다.
