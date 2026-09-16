# Week 2 — 출장비 증빙 검토 (난이도 2/5)

## 완성 프로젝트

정책 citation과 조건 분기를 포함한 3-Agent 검토 서비스. 전체 구현 코드는 `labs/week2_*.py`, 자동 검증은 `tests/test_week2_*.py`에 있습니다.

## Agent 흐름

```text
Retriever → Policy Reviewer → Risk Router
```

## 실습 순서

1. `01_fastapi.ipynb`: API 계약과 endpoint
2. `02_rag.ipynb`: fixture retrieval과 citation
3. `03_agents.ipynb`: 역할별 판단과 routing
4. `04_deployment.ipynb`: health/smoke test

## 실행

```bash
.venv/bin/uvicorn labs.week2_expense_review:app --port 8012
.venv/bin/python -m unittest tests/test_week2_*.py -v
```

## 완료 기준

- 전체 코드 실행
- 해당 notebook 4개를 순서대로 실행
- test 통과
- `deploy/week2.compose.yaml`의 health endpoint 확인
