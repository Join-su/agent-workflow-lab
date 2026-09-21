# Week 2 — 출장비 청구 사전 검토 (난이도 2/5)

## 프로젝트 결과

출장비 청구를 category·priority로 구조화하고, 해당 category의 합성 규정만 검색해 읽기 전용 사전 검토 결과를 만듭니다. 영수증이 없으면 보완 요청, 긴급 건은 관리자 검토로 보냅니다. 지급·환급·전표 생성은 실행하지 않습니다.

```text
classify → category-filtered retrieval → evidence check → review → route
                                                                  ├→ clarify (영수증 보완)
                                                                  ├→ manager_review (긴급)
                                                                  ├→ next_step
                                                                  └→ insufficient_evidence
```

## 선행 조건 — 반복 설명하지 않는 것

Week 1의 Pydantic/FastAPI 기초, `Document`, splitter, 기본 retrieval, citation, 선형 graph는 이미 알고 있다고 가정합니다.

## 이번 주에 새로 배우는 것

- `ExpenseClassification` structured output
- richer domain state와 분류 결과 소유권
- pgvector metadata `filter` (`metadata_filter={"category": ...}`)
- `add_conditional_edges`와 실제 종료 node
- transport/lodging/meal/other 다중 경로 평가
- category·route·citation 일관성 검사
- 검색 근거가 없으면 모델 요약을 호출하지 않고 `insufficient_evidence`로 종료

## 핵심 코드

- `ExpenseRequest`: 청구 입력 계약
- `ExpenseClassification`: 제한된 category·priority 결과 (`Literal`)
- `classify_expense()`: fixture는 결정적 규칙, live는 `generate_structured`. 허용 값 밖이면 실패로 드러냄
- `policy_retriever_node`: 분류된 category로 검색 후보를 먼저 좁힘
- `evidence_extractor_node`: 영수증 확인은 모델이 아닌 결정론적 규칙
- `ExpenseState`: 분류·근거·보완·route 상태
- `build_graph()`: 조건부 종료 graph
- `run_expense_review()`: API·자동 테스트의 canonical 진입점. Notebook에서는 호출하지 않음

## Notebook 순서

1. `01_structured_ticket_classification.ipynb` — 자연어를 제한된 schema로 변환
2. `02_metadata_filtered_retrieval.ipynb` — category filter로 오인용 억제
3. `03_conditional_resolution_routing.ipynb` — 실제 조건부 edge 비교
4. `04_ticket_workflow_evaluation.ipynb` — 다중 경로 회귀 평가

Notebook은 Week 1과 같은 LangGraph를 다시 사용하더라도 선형 edge가 아닌 conditional routing을 직접 구성합니다. 마지막 평가는 app 호출 대신 `classify → filtered retrieval → evidence gate → route`의 꼭 필요한 축소 pipeline을 조립합니다.

## 실행·완료 기준

```bash
.venv/bin/python -m unittest week2.tests.test_expense_workflow -v
APP_MODE=fixture .venv/bin/uvicorn week2.app:app --port 8012
curl -s -X POST http://127.0.0.1:8012/review \
  -H 'content-type: application/json' \
  -d '{"amount":90000,"receipt_attached":true,"purpose":"부산 채용 설명회 숙박비"}'
```

완료 기준:

- 숙박 청구는 숙박 playbook만, 교통 청구는 교통 playbook만 인용한다.
- 영수증이 없으면 `clarify`와 `receipt_required`를 반환한다.
- 긴급 건은 `next_step`이 아니라 `manager_review`로 간다.
- 분류 category와 citation의 문서 category가 일치한다.
- 상한을 넘는 금액은 422로 거부된다.
- 4개 Notebook에서 Week 1 기초를 재강의하지 않고 새 개념을 설명할 수 있다.

Week 3는 이 structured routing을 선행 조건으로 두고 역할별 Agent·bounded loop·HITL 안전 제어를 추가합니다.
