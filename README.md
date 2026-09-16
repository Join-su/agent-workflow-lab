# RAG Multi-Agent Weekly Labs

3주 동안 **매주 독립된 하나의 RAG 멀티 에이전트 서비스**를 완성하고, FastAPI와 Docker 기반 배포 검증까지 반복하는 실습 저장소입니다.

> 난이도는 1~5 척도입니다. 이 저장소는 3주 과정이므로 `1 → 2 → 3`으로 한 주에 한 단계씩 올립니다. Level 4~5는 이 3주 완료 뒤의 확장 과제로 남깁니다.

## 먼저 전체 코드를 실행하기

```bash
uv sync
.venv/bin/python -m unittest discover -s tests -v

# Week 1 / 2 / 3 중 하나 실행
.venv/bin/uvicorn labs.week1_policy_qa:app --port 8011
.venv/bin/uvicorn labs.week2_expense_review:app --port 8012
.venv/bin/uvicorn labs.week3_change_request:app --port 8013
```

모든 구현 코드는 `labs/`에 공개되어 있습니다. notebook은 그 코드를 대체하지 않고 FastAPI, RAG, Agent, 배포를 파트별로 재현·수정하는 실습 자료입니다.

## 프로젝트 지도

| 주차 | 난이도 | 완성 프로젝트 | 멀티 에이전트 흐름 | 배포 확인 |
|---|---:|---|---|---|
| 1 | 1/5 | 규정 Q&A | Retriever → Answer | FastAPI + Docker Compose |
| 2 | 2/5 | 출장비 증빙 검토 | Retriever → Policy Reviewer → Risk Router | FastAPI + Docker Compose |
| 3 | 3/5 | 변경 요청 안전 검토 | Planner → Evidence Reviewer → Risk Reviewer → Synthesizer | FastAPI + Docker Compose |

## 학습 방식

1. 먼저 해당 주 `labs/weekN_*.py`의 완성 코드를 실행합니다.
2. `notebooks/weekN/01_fastapi.ipynb → 02_rag.ipynb → 03_agents.ipynb → 04_deployment.ipynb` 순서로 동작을 분해해 실습합니다.
3. `tests/test_weekN_*.py`를 읽고, 입력을 바꾼 뒤 테스트를 추가합니다.
4. `deploy/weekN.compose.yaml`로 컨테이너 기동·health check를 확인합니다.

## 안전 경계

- fixture 문서만 사용하며 실제 업무 문서·개인정보를 넣지 않습니다.
- 모든 Tool은 읽기 전용입니다.
- 권한·정책 우회 요청은 자동 실행하지 않고 `clarify` 또는 `human_review`로 끝납니다.
- `.env`와 실제 API key는 커밋하지 않습니다.

## 현재 검증 범위

- FastAPI API와 deterministic fixture workflow는 자동 테스트로 검증합니다.
- Docker Compose 파일은 제공하지만, 이 서버에는 Compose plugin이 없어 컨테이너 기동 검증은 아직 하지 못했습니다.
