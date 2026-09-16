# Week 1 — LangChain 규정 RAG·근거 검증 Graph (난이도 1/5)

## 목표

작은 휴가 규정 corpus를 LangChain `Document`와 text splitter로 다루고, LangGraph `QueryState`에서 `Retriever → Answer → Evidence Guard`를 실행합니다.

```text
question → Retriever → Answer → Evidence Guard → answered / insufficient_evidence
```

## 현업 적용 시나리오

**HR 운영팀의 휴가 규정 셀프서비스 보조**를 가정합니다. 구성원이 휴가 신청 기한·승인 조건을 묻고, HR 담당자는 답변이 실제 규정 문서에 연결되는지 확인합니다.

- 사용자: 구성원, HR 운영 담당자
- 입력: 자연어 휴가 규정 질문
- 산출: 규정 citation이 있는 안내 또는 근거 부족 안내
- 실패 비용: 근거 없는 답변이 잘못된 신청·문의 재작업으로 이어짐
- 자동화 경계: 휴가를 신청·승인하지 않고 정보 제공만 수행

API 응답의 `business_use_case`는 `hr_leave_policy_self_service`입니다.

## 왜 1/5인가

최소 3개 역할을 실제 `StateGraph`로 분리하지만, 조건 루프·Tool·권한 판단은 넣지 않습니다. 이 주의 목표는 Agent 수가 아니라 **문서 근거·상태·안전 종료의 계약**입니다.

## 코드에서 확인할 것

- LangChain: `Document`, `RecursiveCharacterTextSplitter`, `RunnableLambda`
- LangGraph: `QueryState`, node, edge, compile, invoke
- FastAPI: `POST /query`, `GET /health`
- 안전성: 근거가 없으면 추측하지 않고 `insufficient_evidence`

## 실행

```bash
uv sync
.venv/bin/python -m unittest week1.tests.test_api -v
.venv/bin/uvicorn week1.app:app --port 8011
```

## Notebook 순서

`01_fastapi → 02_langchain_rag → 03_langgraph_workflow → 04_agent_evaluation → 05_deployment_testing`

## 완료 기준

- [ ] 지원 질문이 `answered`와 citation을 반환한다.
- [ ] 근거 부족 질문이 `insufficient_evidence`로 끝난다.
- [ ] 응답에 `workflow_engine: langgraph`와 3개 역할 실행 기록이 있다.
- [ ] 자동 테스트를 통과한다.

## 다음 주 준비

Week 2에서는 `ExpenseState`와 `conditional edge`를 도입해 `clarify` 또는 `approved_for_next_step`을 선택합니다.

## 배포 경계

`deploy/compose.yaml`은 artifact다. 현재 환경에서 Docker Compose runtime build·기동은 검증하지 않았다.
