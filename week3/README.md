# Week 3 — 운영 장애 대응 멀티에이전트 지휘 시스템 (난이도 3/5)

## 프로젝트 결과

합성 운영 장애를 triage agent, investigator agent, commander agent, risk guard가 명시적 state로 협업해 검토합니다. 시스템은 관찰·검토용 proposal과 사람 승인 packet만 만들며 명령을 실행하지 않습니다.

```text
triage_agent → investigator_agent → commander_agent → risk_guard
                                      ↑                 │
                                      └── revise once ──┤
                                                        └→ finish / blocked
```

## 선행 조건 — 반복 설명하지 않는 것

Week 1의 기본 RAG·citation·API와 Week 2의 structured output·metadata filter·conditional routing을 알고 있다고 가정합니다.

## 이번 주에 새로 배우는 것

- 역할별 Agent 계약과 `IncidentState` 필드 소유권
- `revision_count`·`max_revisions` 종료 invariant
- 조건부 재검토 loop와 fail-closed
- `dry_run` flag + 관찰 명령 allowlist 이중 검사
- SEV1/SEV2 `human_approval_required`
- SEV1/SEV2 `approval_packet`, SEV3 `observation_plan`, audit trace
- shell 제어 문자·복합 명령 차단과 항상 비어 있는 `executed_commands`
- 빈 proposal·파괴 명령·잘못된 severity 실패 테스트

## 핵심 코드

- `IncidentRequest`, `TriageDecision`, `CommandProposal`: 구조화 경계
- `IncidentServices`: 역할 구현의 fixture/live 주입점
- `IncidentState`: 근거·판단·proposal·재검토 횟수 공유 상태
- `proposal_is_safe`: 모델이 붙인 flag만 신뢰하지 않는 결정적 정책
- `risk_guard`: revise/finish/blocked 상태 결정
- `run_incident_response()`: canonical 진입점, 항상 `executed_commands: []`

## Notebook 순서

1. `01_multi_agent_state_ownership.ipynb` — 역할과 state 소유권
2. `02_bounded_revision_loop.ipynb` — 한 번의 재검토와 종료 보장
3. `03_command_safety_human_approval.ipynb` — 파괴 명령 차단·사람 승인
4. `04_incident_workflow_failure_tests.ipynb` — 빈 결과·잘못된 입력·비실행 불변조건

## 실행·완료 기준

```bash
.venv/bin/python -m unittest week3.tests.test_incident_command -v
APP_MODE=fixture .venv/bin/uvicorn week3.app:app --port 8013
curl -s -X POST http://127.0.0.1:8013/incidents/respond \
  -H 'content-type: application/json' \
  -d '{"service":"checkout","summary":"Errors after deployment","severity":"SEV1"}'
```

완료 기준:

- SEV1 첫 위험 제안은 한 번 수정되고 안전한 관찰 proposal만 사람 검토에 남는다.
- 지속적인 위험 proposal과 빈 proposal은 `blocked_manual_review`로 닫힌다.
- `dry_run=True`인 파괴·복합 shell 명령도 allowlist를 통과하지 못한다.
- SEV1/SEV2는 사람 승인이 필요하고 SEV3는 응답의 `observation_plan`으로 관찰 계획을 전달한다.
- 모든 경로에서 `executed_commands == []`이다.
- 4개 Notebook이 이전 주차 기초를 반복하지 않고 고급 제어를 설명한다.

실제 Kubernetes client, shell/subprocess, 운영 credential, 자동 실행은 이 3/5 과정의 명시적 제외 범위입니다.
