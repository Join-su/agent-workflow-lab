# Week 3 — LangGraph 제한 재검토·HITL 변경 검토 (난이도 3/5)

## 목표

보안 변경 요청을 LangChain policy evidence와 LangGraph `ChangeState`로 검토하고, 제한된 재검토 뒤 `done` 또는 `human_review`로 명시적으로 종료합니다.

```text
Planner → Evidence Reviewer → Risk Reviewer
   ↑                              ↓
   └──── bounded revise ─────→ Synthesizer → done / human_review
```

## 현업 적용 시나리오

**IT 운영팀의 변경 요청 위험 검토·승인 준비**를 가정합니다. 운영자는 배포·설정 변경 요청을 제출하고, 시스템은 정책 근거와 위험 사유를 정리해 권한 있는 승인자에게 판단 packet을 제공합니다.

- 사용자: 서비스 운영자, 보안 검토자, 변경 승인자
- 입력: 변경 요청, 요청자 역할
- 산출: 완료 가능한 검토 결과 또는 `human_review_packet`
- 실패 비용: 보안·권한 예외가 검증 없이 운영 변경으로 이어짐
- 자동화 경계: 배포·설정 변경·정책 예외 승인을 절대 수행하지 않음

API 응답의 `business_use_case`는 `it_change_risk_review`입니다.

## 왜 3/5인가

Week 2의 조건 분기에 **shared state, bounded loop, 역할 계약, 사람 승인 경계**가 더해집니다. 핵심은 여러 Agent가 아니라, 누가 어떤 상태를 쓰고 어떤 조건에서 다시 계획하며 언제 반드시 끝나는지 증명하는 것입니다.

## Week 2 대비 새 개념

- `ChangeState`와 역할별 읽기·쓰기 책임
- planner로 되돌아가는 conditional loop
- `revision_count` 상한
- `human_review_packet`과 자동 실행 금지
- 종료 경로 회귀 테스트

## 실행

```bash
# repository root에서 한 번만 실행
uv venv
uv pip install -r requirements.txt

.venv/bin/python -m unittest week3.tests.test_api -v
.venv/bin/uvicorn week3.app:app --port 8013
```

## Notebook 순서

`01_fastapi → 02_langchain_rag → 03_langgraph_workflow → 04_agent_evaluation → 05_deployment_testing`

## 완료 기준

- [ ] 정책 우회 요청이 최대 1회 revise 후 `human_review`로 끝난다.
- [ ] packet에 citation, reason, decision_needed가 있다.
- [ ] 일반 요청은 `done`으로 종료한다.
- [ ] Graph loop·termination contract test를 통과한다.

## Level 4~5 확장

다음 단계는 실제 embedding/vector store·retrieval evaluation·trace 분석(Level 4), MCP·권한·CI·운영 검증(Level 5)이다. 실제 외부 변경은 별도 승인이 필요하다.

## 배포 경계

`deploy/compose.yaml`은 artifact다. 현재 환경에서 Docker Compose runtime build·기동은 검증하지 않았다.
