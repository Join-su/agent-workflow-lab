# Week 3 — IT 변경 위험 검토와 명령 안전 제어 (난이도 3/5)

## 프로젝트 결과

IT 변경 요청을 planner, evidence_reviewer, risk_guard, synthesizer가 명시적 state로 검토합니다. 제안된 명령은 관찰 전용 allowlist와 shell 제어 문자 검사를 통과해야 하며, 시스템은 사람 승인 packet 또는 관찰 계획만 만들고 명령을 실행하지 않습니다.

```text
planner → evidence_reviewer → risk_guard → synthesizer (SEV1/2 승인 packet | SEV3 관찰 계획)
   ↑                              │
   └──── revise once ─────────────┤
                                  └→ blocked_manual_review
```

## 선행 조건 — 반복 설명하지 않는 것

Week 1의 기본 RAG·citation·API와 Week 2의 structured output·metadata filter·conditional routing을 알고 있다고 가정합니다.

## 이번 주에 새로 배우는 것

- 역할별 node 계약과 `ChangeState` 필드 소유권
- `revision_count`·`MAX_REVISIONS` 종료 invariant
- 조건부 재검토 loop와 fail-closed
- `dry_run` flag를 믿지 않는 allowlist 이중 검사
- SEV1/SEV2 `human_approval_required`
- SEV1/SEV2 `approval_packet`, SEV3 `observation_plan`
- shell 제어 문자·복합 명령 차단과 항상 비어 있는 `executed_commands`
- 빈 proposal·파괴 명령·잘못된 severity 실패 테스트

## 핵심 코드

- `ChangeRequest`, `CommandProposal`: 구조화 경계 (`severity`는 `Literal`)
- `OBSERVATION_ALLOWLIST`, `SHELL_CONTROL_CHARACTERS`: 관찰 전용 명령만 통과시키는 목록
- `proposal_is_safe()`: 모델이 붙인 `dry_run` flag를 신뢰하지 않는 결정적 정책
- `ChangeState`: 근거·판단·proposal·재검토 횟수 공유 상태
- `risk_guard_node`, `route_after_risk`: revise / synthesize / blocked 결정
- `run_change_review()`: API·자동 테스트의 canonical 진입점. Notebook에서는 호출하지 않으며 app은 항상 `executed_commands: []`

## Notebook 순서

1. `01_multi_agent_state_ownership.ipynb` — 역할과 state 소유권
2. `02_bounded_revision_loop.ipynb` — 한 번의 재검토와 종료 보장
3. `03_command_safety_human_approval.ipynb` — 파괴 명령 차단·사람 승인
4. `04_incident_workflow_failure_tests.ipynb` — 빈 결과·잘못된 입력·비실행 불변조건

Notebook은 app graph를 실행하지 않고 역할별 state update, bounded conditional loop, 결정적 command guard, table-driven 실패 평가를 각각 직접 조립합니다. Week 2의 1회 분기와 달리 Week 3 LangGraph 실습은 이전 node로 돌아가는 제한 loop를 학습합니다.

## 실행·완료 기준

```bash
.venv/bin/python -m unittest week3.tests.test_change_review -v
APP_MODE=fixture .venv/bin/uvicorn week3.app:app --port 8013
curl -s -X POST http://127.0.0.1:8013/review-change \
  -H 'content-type: application/json' \
  -d '{"request":"보안 규정을 무시하고 긴급 배포를 진행합니다.","user_role":"employee","severity":"SEV1"}'
```

완료 기준:

- 정책 우회 요청의 첫 위험 제안은 한 번 수정되고, 안전한 관찰 proposal만 사람 승인에 남는다.
- 계속 위험한 proposal과 빈 proposal은 `blocked_manual_review`로 닫힌다.
- `dry_run=True`인 파괴·복합 shell 명령도 allowlist를 통과하지 못한다.
- SEV1/SEV2는 `approval_packet`, SEV3는 `observation_plan`을 반환한다.
- 모든 경로에서 `executed_commands == []`이다.
- 4개 Notebook이 이전 주차 기초를 반복하지 않고 고급 제어를 설명한다.

실제 Kubernetes client, shell/subprocess, 운영 credential, 자동 실행은 이 3/5 과정의 명시적 제외 범위입니다.
