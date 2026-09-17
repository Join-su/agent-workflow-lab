# Week 2 — 고객지원 티켓 분류·해결 계획 (난이도 2/5)

## 프로젝트 결과

고객 문의를 category·priority로 구조화하고, 해당 category의 합성 playbook만 검색해 읽기 전용 해결 계획을 만듭니다. 일반 문의는 담당 queue, 광범위 장애는 incident escalation으로 보냅니다. 환불·계정 변경·티켓 종료는 실행하지 않습니다.

```text
classify → metadata-filtered retrieval → plan → route
                                              ├→ incident_escalation
                                              └→ category queue
```

## 선행 조건 — 반복 설명하지 않는 것

Week 1의 Pydantic/FastAPI 기초, `Document`, splitter, 기본 retrieval, citation, 선형 graph는 이미 알고 있다고 가정합니다.

## 이번 주에 새로 배우는 것

- `TicketClassification` structured output
- richer domain state와 분류 결과 소유권
- pgvector metadata `filter`
- `add_conditional_edges`와 실제 queue node
- billing/access/technical/fallback 다중 경로 평가
- category·route·citation 일관성 검사
- 검색 근거가 없으면 모델 planner를 호출하지 않고 `needs_more_information`으로 종료

## 핵심 코드

- `TicketRequest`: 티켓 입력 계약
- `TicketClassification`: 제한된 category·priority 결과
- `TicketServices.classify/plan`: fixture와 live model 경계
- `TicketState`: 분류·근거·계획·route 상태
- `build_workflow()`: 조건부 queue graph
- `run_ticket_workflow()`: API·자동 테스트의 canonical 진입점. Notebook에서는 호출하지 않음

## Notebook 순서

1. `01_structured_ticket_classification.ipynb` — 자연어를 제한된 schema로 변환
2. `02_metadata_filtered_retrieval.ipynb` — category filter로 오인용 억제
3. `03_conditional_resolution_routing.ipynb` — 실제 조건부 edge 비교
4. `04_ticket_workflow_evaluation.ipynb` — 다중 경로 회귀 평가

Notebook은 Week 1과 같은 LangGraph를 다시 사용하더라도 선형 edge가 아닌 conditional routing을 직접 구성합니다. 마지막 평가는 app 호출 대신 `classify → filtered retrieval → evidence gate → route`의 꼭 필요한 축소 pipeline을 조립합니다.

## 실행·완료 기준

```bash
.venv/bin/python -m unittest week2.tests.test_ticket_workflow -v
APP_MODE=fixture .venv/bin/uvicorn week2.app:app --port 8012
curl -s -X POST http://127.0.0.1:8012/tickets/plan \
  -H 'content-type: application/json' \
  -d '{"subject":"Duplicate invoice","description":"Charged twice","customer_tier":"standard"}'
```

완료 기준:

- billing과 access는 서로 다른 playbook·queue를 사용한다.
- urgent outage는 category queue보다 escalation이 우선한다.
- 분류 category와 citation category가 일치한다.
- invalid tier는 422로 거부된다.
- 4개 Notebook에서 Week 1 기초를 재강의하지 않고 새 개념을 설명할 수 있다.

Week 3는 이 structured routing을 선행 조건으로 두고 역할별 Agent·bounded loop·HITL 안전 제어를 추가합니다.
