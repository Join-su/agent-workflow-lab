# Week 2 — LangChain 정책 RAG·조건 라우팅 Graph (난이도 2/5)

## 목표

출장비 정책 근거를 LangChain document로 읽고, LangGraph `ExpenseState`에서 누락 증빙에 따라 다음 경로를 선택합니다.

```text
Policy Retriever → Evidence Extractor → Policy Reviewer → Risk Router
                                                     ├→ clarify
                                                     └→ approved_for_next_step
```

## 현업 적용 시나리오

**재무 운영팀의 출장비 정산 사전 검토**를 가정합니다. 직원이 정산 요청을 제출하면, 담당자는 영수증·업무 목적 같은 최소 증빙이 갖춰졌는지 먼저 분류합니다.

- 사용자: 출장자, 재무 운영 담당자
- 입력: 금액, 영수증 첨부 여부, 업무 목적
- 산출: 보완 요청 또는 다음 검토 단계 전달과 정책 citation
- 실패 비용: 불완전한 정산의 반복 반려·지급 지연·감사 추적성 저하
- 자동화 경계: 지급·승인·회계 전표 처리는 수행하지 않음

API 응답의 `business_use_case`는 `expense_claim_precheck`입니다.

## 왜 2/5인가

Week 1의 선형 근거 검증에 **공유 state와 `add_conditional_edges`**를 추가합니다. 비용 지급·승인은 수행하지 않으며, Agent는 근거 있는 보완 요청 또는 다음 검토 단계 전달만 합니다.

## Week 1 대비 새 개념

- `ExpenseState`의 상태 소유권
- `missing`, `citations`, `route`를 분리하는 구조화된 review state
- terminal node와 conditional edge
- `clarify`를 안전한 보류 경로로 다루는 방법

## 실행

```bash
# repository root에서 한 번만 실행
uv venv
uv pip install -r requirements.txt

.venv/bin/python -m unittest week2.tests.test_api -v
.venv/bin/uvicorn week2.app:app --port 8012
```

## Notebook 순서

`01_fastapi → 02_langchain_rag → 03_langgraph_workflow → 04_agent_evaluation → 05_deployment_testing`

## 완료 기준

- [ ] 영수증 누락은 `clarify`, `receipt_required`로 끝난다.
- [ ] 충족 입력은 `approved_for_next_step`으로 간다.
- [ ] citation과 4개 Agent 실행 기록이 반환된다.
- [ ] 두 경로의 graph contract test가 있다.

## 다음 주 준비

Week 3에서는 conditional edge를 loop로 확장하되 `revision_count`로 재검토를 제한하고, 위험한 결론은 사람 검토 packet으로 넘깁니다.

## 배포 경계

`deploy/compose.yaml`은 artifact다. 현재 환경에서 Docker Compose runtime build·기동은 검증하지 않았다.
