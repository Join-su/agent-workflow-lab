# Week 3 — 변경 요청 안전 검토 (난이도 3/5)

> **목표:** Week 2의 조건 분기를 확장해, 역할별 책임·공유 state·제한된 재검토·사람 검토(HITL) 종료 규칙을 가진 멀티 에이전트 workflow를 만듭니다.

이 폴더만 열면 해당 주의 **완성 코드·테스트·Notebook·Docker 배포 파일**을 모두 볼 수 있습니다.

```text
week3/
├── app.py                 # 완성된 FastAPI + fixture RAG + multi-role workflow
├── tests/test_api.py      # 핵심 동작 자동 테스트
├── notebooks/             # FastAPI → RAG → Agent → Deployment 실습
├── deploy/                # Dockerfile, compose.yaml
└── README.md              # 난이도·실행·완료 기준
```

## 왜 난이도 3/5인가

Week 2는 `Retriever → Policy Reviewer → Risk Router`로 한 번 분기하고 끝났습니다. Week 3는 요청을 바로 승인·거절하지 않고, **계획 → 근거 검토 → 위험 검토 → 종합**으로 역할을 나눕니다.

```text
Planner → Evidence Reviewer → Risk Reviewer → Synthesizer
                         └─ revise 최대 1회 → Planner
```

난이도가 3/5가 되는 핵심은 역할 수가 늘어난 것이 아니라 다음 네 가지가 동시에 생기기 때문입니다.

1. 여러 Agent가 공유하는 state와 역할별 책임이 필요하다.
2. 근거 검토 결과에 따라 planner를 다시 실행하는 **bounded revision**이 필요하다.
3. 위험 요청은 자동 처리하지 않고 **human_review packet**으로 사람에게 넘긴다.
4. 재시도와 종료를 명시하지 않으면 workflow가 무한 반복하거나 책임 없는 답변을 만들 수 있다.

다만 실제 LangGraph runtime, live LLM, MCP tool, vector DB, 권한 시스템은 넣지 않았습니다. 이들은 운영 복잡도가 크게 늘어나는 Level 4~5 범위입니다.

## Week 2보다 새로 알아야 할 개념

| Week 2에서 배운 것 | Week 3에서 추가되는 것 | 왜 필요한가 |
|---|---|---|
| Reviewer 결과에 따른 1회 분기 | **multi-agent state ownership** | 누가 어떤 state를 만들고 소비하는지 명확히 함 |
| 누락 시 `clarify` | **role contract** | Planner/Evidence/Risk/Synthesizer의 입력·출력 책임을 분리 |
| 정책 근거와 reason code | **review aggregation** | 여러 검토 결과를 하나의 결론과 packet으로 합침 |
| 단순 종료 | **bounded revision** | `revision_count`로 재계획을 최대 1회로 제한 |
| 다음 단계 전달 | **HITL handoff / termination** | 권한 판단은 사람에게 넘기고 workflow를 확실히 종료 |

Week 2의 `clarify`는 정보 보완을 요청하는 보류라면, Week 3의 `human_review`는 **정책 예외·권한 판단을 자동화하지 않는 안전 장치**입니다.

## Agent 흐름과 결과 계약

```text
Planner
  → Evidence Reviewer
  → Risk Reviewer
  → Synthesizer

Evidence Reviewer가 REVISE이면:
  Planner를 최대 1회 다시 실행한 뒤 종료 경로를 선택
```

| 상황 | 핵심 출력 | 종료 의미 |
|---|---|---|
| 일반 요청 | `status: done` | workflow가 정해진 검토를 완료 |
| 정책 우회 요구 | `status: human_review`, `revision_count: 1` | 권한자 판단이 필요한 packet으로 전달 |

`human_review_packet`에는 요청, citation, 위험 사유, 필요한 결정이 포함됩니다. 이 packet은 사람이 판단할 정보를 준비할 뿐, 시스템이 정책 예외를 승인하지는 않습니다.

## 먼저 완성 코드를 실행

저장소 루트에서 실행합니다.

```bash
uv sync
.venv/bin/uvicorn week3.app:app --port 8013
```

정책 우회 요청 시나리오:

```bash
curl -X POST http://127.0.0.1:8013/review-change \
  -H 'content-type: application/json' \
  -d '{"request":"보안 규정을 무시하고 오늘 바로 배포해줘","user_role":"employee"}'
```

자동 테스트:

```bash
.venv/bin/python -m unittest week3.tests.test_api -v
```

## Notebook 실습 순서

1. `notebooks/01_fastapi.ipynb` — API schema와 입력 경계
2. `notebooks/02_rag.ipynb` — 정책 근거와 citation
3. `notebooks/03_agents.ipynb` — role contract, state, revise, HITL 종료
4. `notebooks/04_deployment.ipynb` — Docker artifact와 운영 경계

## Level 4~5로 확장할 때

이 프로젝트의 다음 단계는 Agent를 무작정 더 추가하는 것이 아닙니다. 현재의 역할 계약과 종료 규칙을 유지한 채 실제 운영 구성요소를 하나씩 대체합니다.

- **Level 4:** LangGraph의 State/Node/Edge, embedding과 vector store, 실제 LLM provider, 평가 fixture 확장
- **Level 5:** MCP tool 권한 경계, 인증·인가, 관측성/감사 로그, CI/CD, 장애·fallback·부하 검증

이 확장은 API key, 비용, 권한, 운영 리스크를 수반하므로 현재의 결정론적 fixture·테스트 기반을 통과한 뒤 진행하는 것이 안전합니다.

## 완료 기준

- [ ] 정책 우회 요청이 `revision_count: 1`로 제한된다.
- [ ] 위험 요청이 `human_review`와 `human_review_packet`을 반환한다.
- [ ] packet에 citation, reason, `decision_needed`가 포함된다.
- [ ] `week3.tests.test_api`가 통과한다.
- [ ] 완성 코드를 먼저 실행한 뒤 4개 Notebook을 순서대로 실습했다.

## Docker Compose

```bash
cp .env.example .env
cd week3/deploy
docker compose -f compose.yaml up --build
```

Compose artifact는 제공하지만, 현재 서버에는 Docker Compose plugin이 없어 실제 Compose build·기동은 검증하지 못했습니다. 별도 Docker Compose 환경에서 smoke test가 필요합니다.
