# Week 2 — 출장비 증빙 검토 (난이도 2/5)

> **목표:** Week 1의 “근거 있는 답변 또는 안전한 종료” 위에, 정책 기준으로 검토하고 누락 사유에 따라 다음 행동을 분기하는 Agent workflow를 만듭니다.

이 폴더만 열면 해당 주의 **완성 코드·테스트·Notebook·Docker 배포 파일**을 모두 볼 수 있습니다.

```text
week2/
├── app.py                 # 완성된 FastAPI + fixture RAG + 3역할 workflow
├── tests/test_api.py      # 핵심 동작 자동 테스트
├── notebooks/             # FastAPI → RAG → Agent → Deployment 실습
├── deploy/                # Dockerfile, compose.yaml
└── README.md              # 난이도·실행·완료 기준
```

## 왜 난이도 2/5인가

Week 1은 `Retriever → Answer`의 선형 흐름이었습니다. Week 2는 여기에 역할을 두 개 더하지만, **복잡한 loop, planner, 다중 검토 집계는 아직 넣지 않습니다.**

```text
Retriever → Policy Reviewer → Risk Router
```

난이도가 한 단계 높아지는 이유는 Agent 수 자체가 아니라, 같은 근거를 보고도 **정책 기준으로 상태를 만들고 그 상태에 따라 다음 행동을 선택**해야 하기 때문입니다.

- `Retriever`: 출장비 정책 근거를 제공
- `Policy Reviewer`: 영수증·업무 목적의 누락을 구조화
- `Risk Router`: 누락이 있으면 `clarify`, 없으면 `approved_for_next_step`

이 범위는 “승인/거절”을 단정하는 시스템이 아니라, 누락된 정보를 안전하게 보완 요청하는 workflow를 배우기에 적절한 Level 2입니다.

## Week 1보다 새로 알아야 할 개념

| Week 1에서 고정한 것 | Week 2에서 추가되는 것 | 왜 필요한가 |
|---|---|---|
| 질문 → 근거 → 답변 | **정책 criterion** | 어떤 조건을 검사할지 명시해야 함 |
| `answered` / `insufficient_evidence` | **구조화된 review state** | 단순 문장이 아니라 `missing` 목록으로 판단 근거를 남김 |
| 단일 안전 종료 | **conditional routing** | 결과에 따라 `clarify` 또는 다음 단계로 분기 |
| citation 반환 | **reason code / follow-up** | 사용자가 무엇을 보완해야 하는지 기계적으로 알 수 있음 |
| 단일 역할 경계 | **read-only review boundary** | 검토 Agent가 비용을 수정·집행하지 않음 |

특히 Week 1의 citation과 명시적 output schema가 흔들리면 Week 2의 Reviewer와 Router는 신뢰할 입력을 받을 수 없습니다.

## Agent 흐름과 결과 계약

```text
Retriever → Policy Reviewer → Risk Router
```

| 입력 상태 | 핵심 출력 | 시스템 행동 |
|---|---|---|
| 영수증 또는 목적 누락 | `status: clarify`, `required_follow_up` | 보완 요청으로 종료 |
| 필수 정보 충족 | `status: approved_for_next_step` | 다음 업무 단계로 전달 가능 |

`approved_for_next_step`은 비용 지급이나 최종 승인을 뜻하지 않습니다. 이 예제의 Agent는 **정보 검토와 routing만** 수행합니다.

## 먼저 완성 코드를 실행

저장소 루트에서 실행합니다.

```bash
uv sync
.venv/bin/uvicorn week2.app:app --port 8012
```

영수증 누락 시나리오:

```bash
curl -X POST http://127.0.0.1:8012/review \
  -H 'content-type: application/json' \
  -d '{"amount":50000,"receipt_attached":false,"purpose":"고객 미팅"}'
```

자동 테스트:

```bash
.venv/bin/python -m unittest week2.tests.test_api -v
```

## Notebook 실습 순서

1. `notebooks/01_fastapi.ipynb` — 입력 schema와 API boundary
2. `notebooks/02_rag.ipynb` — 정책 근거와 citation
3. `notebooks/03_agents.ipynb` — Reviewer state와 Risk Router 분기
4. `notebooks/04_deployment.ipynb` — Docker artifact와 실행 경계

## Week 3로 넘어가기 전 준비

Week 3에서는 Reviewer가 만든 판단을 여러 역할이 공유하고, revise 횟수를 제한한 뒤 사람 검토 packet으로 종료합니다. 따라서 아래를 설명할 수 있어야 합니다.

- 판단 결과를 자연어만이 아니라 명시적인 **state**로 저장하는 이유
- `clarify`처럼 안전한 보류 경로가 최종 승인보다 먼저 필요한 이유
- routing 조건과 누락 사유 코드를 테스트로 고정하는 방법
- Agent가 검토할 수 있는 일과, 권한자에게 넘겨야 하는 일을 구분하는 방법

## 완료 기준

- [ ] 영수증 누락 요청이 `clarify`와 `receipt_required`를 반환한다.
- [ ] 충족 요청이 `approved_for_next_step`으로 분기한다.
- [ ] 응답에 정책 citation이 유지된다.
- [ ] `week2.tests.test_api`가 통과한다.
- [ ] 완성 코드를 먼저 실행한 뒤 4개 Notebook을 순서대로 실습했다.

## Docker Compose

```bash
cp .env.example .env
cd week2/deploy
docker compose -f compose.yaml up --build
```

Compose artifact는 제공하지만, 현재 서버에는 Docker Compose plugin이 없어 실제 Compose build·기동은 검증하지 못했습니다. 별도 Docker Compose 환경에서 smoke test가 필요합니다.
