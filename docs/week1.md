# Week 1 — 규정 Q&A (난이도 1/5)

## 완성 프로젝트

가장 단순한 RAG 기반 2-Agent 답변 서비스. 전체 구현 코드는 `labs/week1_*.py`, 자동 검증은 `tests/test_week1_*.py`에 있습니다.

## Agent 흐름

```text
Retriever → Answer
```

## 실습 순서

1. `01_fastapi.ipynb`: API 계약과 endpoint
2. `02_rag.ipynb`: fixture retrieval과 citation
3. `03_agents.ipynb`: 역할별 판단과 routing
4. `04_deployment.ipynb`: health/smoke test

## 실행

```bash
.venv/bin/uvicorn labs.week1_policy_qa:app --port 8011
.venv/bin/python -m unittest tests/test_week1_*.py -v
```

## 완료 기준

- 전체 코드 실행
- 해당 notebook 4개를 순서대로 실행
- test 통과
- `deploy/week1.compose.yaml`의 health endpoint 확인
