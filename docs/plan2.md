# 교육활용자료2 구축 계획

- 상태: 구현 전 계획
- Project 주제: 승인됨
- 구현·Remote·Commit·Push·Live API 실행: 미승인
- 대상 경로 제안: `/opt/data/agent-workflow-lab-v2`
- 목표: 기본 RAG 이후 한화내일아카데미 커리큘럼을 3개의 독립 현업 Project와 별도 기술 학습 Notebook으로 구현

---

## 1. 목표와 고정 원칙

### 목표

매주 현업에서 사용할 수 있는 독립 Project 하나를 완성하고, 해당 Project에 필요한 기술을 `notebooks/`에서 별도 실습한다.

```text
Week 1: 측정 가능한 Advanced RAG
→ Week 2: 안전한 Function Calling·Tool·MCP Agent
→ Week 3: 지속·재개 가능한 Multi-Agent·HITL·Enterprise Delivery
```

### Project와 Notebook의 역할 분리

- **Project:** 사용자·현업 문제·입력·업무 흐름·결과 화면·안전 경계를 갖춘 완성 App이다.
- **Notebook:** Project에 필요한 기술을 작은 독립 시나리오로 직접 조립하는 학습 자료다.
- Notebook은 완성 App을 호출하는 사용 데모가 아니다.
- Project 주제·API 계약과 Notebook 학습 목표는 연결하되, 구현 코드는 서로 독립시킨다.

### 전체 안전 경계

- 합성 Fixture와 공개 가능한 가상 문서만 사용한다.
- 실제 회사 문서·개인정보·운영 Credential을 사용하지 않는다.
- 실제 구매·결제·승인·QMS/MES 변경·Shell/Kubernetes 실행을 하지 않는다.
- 외부 Write Tool을 연결하지 않는다.
- Fixture, Mock, Live 실행 결과를 서로 다른 증거로 보고한다.

---

## 2. 이전 교육활용자료에서 수정이 많았던 부분과 예방 규칙

| 이전 문제 | 실제 영향 | 교육활용자료2 예방 규칙 | 검증 Gate |
|---|---|---|---|
| Week 2·3 App 주제와 README·Notebook·Test 주제가 달라짐 | 무엇이 정본인지 불명확하고 기존 Symbol Import 오류 발생 | 주차별 Project ID·도메인·Endpoint·Symbol·Notebook 목록을 `curriculum_manifest.yaml` 하나에서 관리 | Manifest와 README·App·Test·Notebook 자동 대조 |
| 상위 README가 존재하지 않는 Notebook 이름을 안내 | 학습 순서가 깨지고 Notebook Test 실패 | 파일 생성 전에 Notebook Inventory를 확정하고 README는 Inventory에서 생성·검사 | Exact Inventory Test |
| 완성 `app.py` 함수 호출 중심 Notebook | 학습자가 Primitive와 Pipeline 연결을 직접 연습하지 못함 | `weekN.app`, 완성 Workflow, App Helper·Request Model Import 금지 | AST 기반 금지 Import·Call 검사 |
| App 전체를 Notebook에 복사하거나 설명만 바꿈 | 독립 실습이 아니라 중복 코드가 되고 주차별 학습 증가분이 사라짐 | 작은 Fixture와 2~3개의 핵심 Code Cell로 Primitive·축소 Pipeline만 직접 구성 | Cell 중복·필수 Primitive·중간 출력 검사 |
| Notebook 제목·설명은 기능을 약속하지만 실제 Cell이 실행하지 않음 | 문서상 Coverage와 실행 가능한 Coverage가 달라짐 | 파일명·학습 목표·실행 Cell·Assertion을 `notebook_contracts.yaml`로 연결 | Artifact-Promise Contract Test |
| Notebook이 실행되지 않은 채 파일 존재만 확인 | JSON은 유효하지만 Runtime 오류를 놓침 | Clean Fixture 환경에서 모든 Notebook을 Top-to-bottom 실행 | `nbclient` 실행·Output/Error 검사 |
| App 변경 후 Stale Test와 UI Assertion이 남음 | 전체 Test 30개 중 실패 3·오류 4 발생 | 기능 변경 시 Test·README·UI Contract를 같은 Vertical Slice에서 갱신 | Target Test→Full Suite 순서, Green 아니면 다음 단계 중단 |
| `uv.lock`의 `tzdata` Source 오류 | `uv sync --frozen` 실패로 재현 가능한 설치 불가 | 지원 Python·uv 버전을 먼저 고정하고 Lockfile을 깨끗한 환경에서 생성·검증 | Fresh Environment의 `uv sync --frozen` |
| Dockerfile·Compose Artifact를 배포 완료로 표현할 위험 | 실제 Runtime·Import·Health 문제가 남을 수 있음 | Artifact 작성과 Build·Run·Smoke Evidence를 구분 | Container Build, Health, API Smoke를 실제 실행한 경우에만 PASS |
| Fixture·Mock 성공을 OpenAI+pgvector Live 성공처럼 해석할 위험 | 실제 Network·DB·Embedding·Citation 경로가 미검증 | Fixture Test와 Live Smoke Job을 별도 실행·보고 | 응답의 `mode`, 실제 문서 ID·Citation Readback |
| Week 3 안전 Guard가 Notebook마다 다르게 구현될 위험 | Mixed Safe/Unsafe Batch에서 일부 위험 명령만 제거하고 나머지를 승인할 수 있음 | Safety Semantics를 Canonical Contract로 고정하고 All-or-nothing Fail-closed 적용 | Mixed Batch·Control Character·빈 Proposal 회귀 Test |
| Review Packet을 실제 HITL로 표현 | Interrupt·Checkpoint·Resume 없이도 HITL 완료로 오인 | Packet 생성과 실행 중단·상태 저장·재개를 별도 Capability로 분류 | Approve·Reject·Edit 후 동일 Thread Resume Test |
| Command 문자열 검사를 Function Calling으로 표현 | Tool Schema·Dispatcher·Observation Loop가 없는 상태를 과대평가 | Tool Binding, 인자 검증, Dispatcher, Observation 환류가 있을 때만 Function Calling으로 표기 | Unknown Tool·Invalid Args·Timeout Test |
| 역할 이름이 다른 Node를 완전한 Multi-Agent로 표현 | Handoff·State Ownership·Failure Isolation이 없음 | Agent별 입력·출력·소유 State·Handoff·Step Budget을 명시 | State Ownership·Handoff·Termination Test |
| Project 설계와 Notebook 설계를 한 질문으로 묶음 | 승인 대상과 학습 자료 설계가 혼동됨 | Project Contract와 Notebook Contract를 별도 문서·Gate로 관리 | Project Approval과 Notebook Review 상태를 별도 기록 |

### 최우선 교훈

1. 기능 추가보다 먼저 정본과 계약을 고정한다.
2. 코드·문서·Notebook·Test를 한 Vertical Slice에서 함께 변경한다.
3. Notebook은 App이 Green이 된 뒤 작성하되 App을 Import하지 않는다.
4. 파일이 존재하는 것과 실행·검증된 것을 구분한다.
5. 작성자가 자신의 작업을 최종 승인하지 않고 독립 Review를 거친다.

---

## 3. Single Source of Truth 설계

구현 시작 시 다음 두 Manifest를 먼저 만든다.

### `curriculum_manifest.yaml`

주차별 아래 값을 고정한다.

- Project ID와 제목
- 난이도
- 사용자·문제·결과물
- FastAPI Endpoint
- Request·Response Model 이름
- 신규 학습 개념
- 재사용하지만 재설명하지 않는 개념
- Notebook Inventory
- Test 파일
- 안전 불변조건
- Fixture·Live 완료 기준

### `notebook_contracts.yaml`

Notebook별 아래 값을 고정한다.

- 파일명
- 학습 목표
- 직접 생성해야 할 Library Primitive
- 실행해야 할 정상·실패 Fixture
- 관찰해야 할 중간값
- Assertion
- 금지 Import·Call
- 실제 App과의 개념적 연결

### 변경 규칙

- Manifest 변경 없이 Project명·Endpoint·Symbol·Notebook 파일명을 바꾸지 않는다.
- Manifest 변경은 관련 README·Test·UI 계약을 함께 수정한다.
- 한 항목이라도 불일치하면 Release Gate를 실패시킨다.

---

## 4. Week 1 Project — 기술지원 지식 검색 품질 개선 서비스

### 난이도

**1/5 — 단일 검색 서비스, 요청 단위 상태, 외부 Tool 없음**

### 현업 문제

기술지원 담당자가 제품 매뉴얼·FAQ·Troubleshooting 문서를 검색하지만 표현 차이, 정확 키워드, Chunk 단절 때문에 적절한 근거를 놓친다.

### 사용자 결과물

- Baseline과 Advanced Retrieval 결과 비교
- Top-k 문서·Score·Citation
- 답변 또는 근거 부족 상태
- 검색 실패 유형
- 평가 지표 비교

### App 흐름

```text
Question
→ Baseline Retrieval
→ Query Rewriting·Multi-Query
→ Hybrid Retrieval·Fusion
→ Parent Context 복원
→ Relevance·Grounding Grade
→ Answer / Rewrite-and-Retrieve / Abstain
```

### 주요 기술

- 고정 평가셋과 Gold Evidence
- Recall@k·MRR
- Query Rewriting
- Multi-Query와 Dedupe
- BM25+Dense Hybrid Retrieval
- Reciprocal Rank Fusion
- Parent Document Retriever
- Self-RAG Quality Gate
- Bounded Retry와 Abstain

### API·UI

- `POST /diagnose`
- `POST /evaluate`
- `GET /diagnostics`
- Streamlit: 검색 전략·중간 Retrieval·평가 비교·Citation 표시

### 관련 기술 학습 Notebook — 5개

1. `01_retrieval_evaluation_baseline.ipynb`
2. `02_query_rewriting_multi_query.ipynb`
3. `03_hybrid_retrieval_fusion.ipynb`
4. `04_parent_document_retrieval.ipynb`
5. `05_self_rag_quality_gate.ipynb`

### Week 1 완료 기준

- 동일 평가셋으로 Baseline과 Advanced 결과를 비교한다.
- 지원·모호·미지원 질문이 다른 Trace를 만든다.
- Citation이 실제 Parent·Source와 일치한다.
- 최대 재검색 횟수 후 안전하게 종료한다.
- 모든 App Test와 5개 Notebook이 실행된다.

---

## 5. Week 2 Project — 기업 구매 요청 검토 Agent

### 난이도

**2/5 — 단일 Agent, 복수 Tool, MCP, Routing·Parallelism**

### 현업 문제

구매 담당자가 구매 요청서와 예산·정책·공급사·카탈로그 정보를 여러 시스템에서 교차 확인한다.

### 사용자 결과물

- 정책 적합성
- 예산 상태
- 공급사 등록 여부
- 카탈로그 비교
- 누락 정보와 예외 사유
- 사람 검토 Queue

Agent는 실제 구매·결제·승인을 수행하지 않는다.

### App 흐름

```text
Purchase Request
→ Classify·Plan
→ Select Tool
→ MCP Read-only Call
→ Validate Observation
→ Parallel Checks
→ Reduce Results
→ Review Packet / Needs More Information
```

### 주요 기술

- JSON Schema Function Calling
- Tool Argument Validation
- Deterministic Dispatcher
- Action→Observation Loop
- Step Budget
- Local MCP Server·Client
- Resource·Tool Discovery
- Prompt Chaining
- Conditional Routing
- Fan-out·Fan-in
- Timeout·Retry·Idempotency
- Unknown Tool Fail-closed

### 허용 Tool

- `get_policy`
- `check_budget`
- `lookup_vendor`
- `compare_catalog`

모든 Tool은 합성 데이터에 대한 Read-only 또는 In-memory Sandbox 동작만 제공한다.

### 관련 기술 학습 Notebook — 5개

1. `01_function_calling_tool_schema.ipynb`
2. `02_action_observation_dispatcher.ipynb`
3. `03_local_mcp_resources_tools.ipynb`
4. `04_chaining_routing_parallel.ipynb`
5. `05_tool_failure_safety.ipynb`

### Week 2 완료 기준

- 정상·누락·예산 초과·미등록 공급사가 서로 다른 Trace를 만든다.
- 허용되지 않은 Tool은 실행 전에 차단된다.
- MCP 장애가 명시적 업무 상태로 변환된다.
- Retry·Step Budget이 종료를 보장한다.
- 모든 App Test와 5개 Notebook이 실행된다.

---

## 6. Week 3 Project — 제조 품질 이상 CAPA Multi-Agent Control Tower

### 난이도

**3/5 — Supervisor·전문 Worker, 지속 상태, 실제 HITL, Enterprise Gate**

### 현업 문제

품질 이상 발생 시 품질·생산·설비·안전 담당자가 서로 다른 근거를 검토해야 하며, CAPA 실행 전 사람의 판단과 추적 가능한 승인이 필요하다.

### 사용자 결과물

- 부서별 조사 결과와 근거
- 상충 Evidence
- CAPA 초안
- Risk Review
- 사람 검토 Packet
- Approve·Reject·Edit 이력
- Audit Ledger

실제 QMS·MES·설비 변경은 수행하지 않는다.

### App 흐름

```text
Quality Event
→ Supervisor
→ Quality·Production·Maintenance·Safety Workers
→ Parallel Evidence Collection
→ Evidence Reducer·Conflict Marker
→ CAPA Planner
→ Risk Reviewer
→ Interrupt·Checkpoint
→ Human Approve / Reject / Edit
→ Resume
→ Action Draft·Audit Ledger
```

### 주요 기술

- Agent별 Input·Output Contract
- State Ownership과 Handoff
- Supervisor·Worker
- Parallel Worker·Reducer
- Partial Failure Isolation
- Conditional Path·Bounded Review
- MCP Role Allowlist
- Checkpoint·Thread ID
- Interrupt·Resume
- Tool Idempotency
- Clean Architecture
- TDD
- SDD Skill Contract
- GitHub PR·Review·CI
- Container·Health·Rollback Artifact

### 관련 기술 학습 Notebook — 6개

1. `01_agent_contracts_handoffs.ipynb`
2. `02_supervisor_parallel_reducer.ipynb`
3. `03_interrupt_checkpoint_resume.ipynb`
4. `04_mcp_permissions_audit.ipynb`
5. `05_tdd_skill_contracts.ipynb`
6. `06_ports_adapters_contract_testing.ipynb`

### Week 3 완료 기준

- Worker 하나가 실패해도 설명 가능한 상태로 종료한다.
- 모든 Graph 경로가 Step Budget 안에 종료한다.
- 사람 승인 전 `executed_actions=[]`이다.
- Approve·Reject·Edit 후 동일 Thread에서 재개한다.
- 재개 시 완료된 Tool을 중복 실행하지 않는다.
- Unit·Contract·Notebook·Fixture Smoke가 CI에서 통과한다.

---

## 7. Notebook 작성 계약

각 Notebook은 다음 순서를 지킨다.

```text
현업 시나리오·학습 목표
→ 작은 독립 Fixture
→ Library Primitive 직접 선언
→ 연결·실행
→ 중간 Evidence·State·Trace 관찰
→ 실패 경계 실행
→ Assertion
→ 실제 App에서 확장되는 위치 설명
```

### 필수 조건

- 유효한 `nbformat: 4`
- Clean Fixture 환경에서 Top-to-bottom 실행
- 최소 정상 1건과 실패 1건 실행
- 중간값을 실제로 출력·검사
- 중요한 Class·Function·State Field 옆에 고유한 설명 주석 배치
- 이전 주 개념은 재설명하지 않고 이번 주 신규 사용 패턴에 집중
- 외부 Side Effect 없음

### 금지 조건

- `from weekN.app import ...`
- 완성 Workflow·`create_app`·`run_*` 호출
- App 전용 Request·Response Model을 학습 중심으로 사용
- App 전체 코드 복사
- 결과만 출력하고 중간 Pipeline을 숨기는 예제
- 문구만 다른 중복 Notebook
- 실행되지 않는 약속·설명만 존재하는 Notebook

### Notebook 자동 검증

- Exact Inventory
- JSON Schema와 Cell Type
- AST 기반 Canonical App Import·Call 금지
- 필수 Primitive 생성 확인
- Top-to-bottom 실행
- 정상·실패 Assertion 확인
- 중복 Code Block과 Boilerplate Comment 검사
- App Safety Semantics와 Notebook Guard의 동등성 검사

---

## 8. TDD 구현 절차

모든 App 기능과 Bug Fix는 다음 순서를 지킨다.

```text
RED: 하나의 행동 Test 작성
→ Test를 실행해 의도한 이유로 실패 확인
→ GREEN: 최소 구현
→ Target Test 통과
→ Full Suite 통과
→ REFACTOR
→ 다음 Vertical Slice
```

### 금지

- Production Code를 먼저 작성한 뒤 Test 추가
- 여러 기능 Test를 한꺼번에 작성한 뒤 일괄 구현
- Test가 처음부터 통과했는데 그대로 진행
- 실패한 Full Suite를 다음 단계에서 고치기로 미루기

### 증거

`docs/tdd-log.md`에 다음만 간단히 기록한다.

- Test 이름
- RED 실패 이유
- GREEN 통과 명령
- Refactor 범위
- Full Suite 결과

---

## 9. 구현 단계와 Gate

### Phase 0 — Bootstrap

1. 새 독립 작업 경로를 만든다.
2. Python·uv 버전을 고정한다.
3. `pyproject.toml`, `uv.lock`, `.env.example`, `.gitignore`를 만든다.
4. `curriculum_manifest.yaml`과 `notebook_contracts.yaml`을 만든다.
5. Manifest Contract Test를 먼저 RED로 만든다.

**Gate 0:** Fresh Environment에서 `uv sync --frozen`이 통과하지 않으면 기능 구현을 시작하지 않는다.

### Phase 1 — Week 1 App

1. API·Domain·Evaluation Contract Test를 RED로 만든다.
2. Fixture Baseline Retrieval을 구현한다.
3. Advanced Retrieval을 Vertical Slice 단위로 추가한다.
4. 전체 Test를 Green으로 만든다.
5. Streamlit→FastAPI Fixture Smoke를 실행한다.
6. App이 Green인 뒤 Week 1 Notebook을 작성·실행한다.

**Gate 1:** App·README·Test·Notebook·Manifest가 모두 일치해야 Week 2로 이동한다.

### Phase 2 — Week 2 App

1. Tool Schema·Dispatcher·Failure Contract Test를 RED로 만든다.
2. In-memory Tool Loop를 먼저 구현한다.
3. Local MCP Server·Client로 교체한다.
4. Routing·Parallelism과 Failure Safety를 추가한다.
5. App이 Green인 뒤 Week 2 Notebook을 작성·실행한다.

**Gate 2:** Unknown Tool·Invalid Args·Timeout·Retry Exhaustion이 모두 Fail-closed여야 Week 3로 이동한다.

### Phase 3 — Week 3 App

1. Agent Contract·Ownership·Termination Test를 RED로 만든다.
2. Supervisor와 Worker Handoff를 구현한다.
3. Parallel Reducer와 Partial Failure를 구현한다.
4. Checkpoint·Interrupt·Resume를 구현한다.
5. TDD·SDD·Ports/Adapters Artifact를 추가한다.
6. App이 Green인 뒤 Week 3 Notebook을 작성·실행한다.

**Gate 3:** Approve·Reject·Edit, 중복 실행 방지, `executed_actions=[]` 불변조건이 모두 통과해야 Release Review로 이동한다.

### Phase 4 — Live·Deployment Verification

1. Fixture 결과를 동결한다.
2. 실제 pgvector Ingest를 수행한다.
3. OpenAI Retrieval·Generation·Citation을 Smoke Test한다.
4. MCP Runtime을 별도 Process에서 Smoke Test한다.
5. Container Build·Health·API Smoke를 실행한다.
6. 실패 시 Fixture PASS와 Live FAIL을 분리해 보고한다.

**Gate 4:** 실제 실행하지 않은 항목은 `artifact-authored`로만 표시하고 `verified`로 표시하지 않는다.

### Phase 5 — 독립 Review

1. Spec Compliance Review
2. Code Quality·Security Review
3. Curriculum·Notebook Review
4. 수정 후 전체 Gate 재실행

작성 Agent와 다른 Reviewer가 검토하며, Security Concern 또는 Logic Error가 남으면 Release하지 않는다.

---

## 10. 저장소 구조

```text
agent-workflow-lab-v2/
├── README.md
├── plan.md
├── curriculum_manifest.yaml
├── notebook_contracts.yaml
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── shared/
│   ├── contracts/
│   ├── evaluation/
│   ├── retrieval/
│   ├── mcp/
│   └── testing/
├── week1/
│   ├── app.py
│   ├── domain.py
│   ├── knowledge/
│   ├── evaluation/
│   ├── notebooks/
│   └── tests/
├── week2/
│   ├── app.py
│   ├── domain.py
│   ├── tools.py
│   ├── mcp_server.py
│   ├── fixtures/
│   ├── notebooks/
│   └── tests/
├── week3/
│   ├── app.py
│   ├── domain.py
│   ├── agents.py
│   ├── checkpoints.py
│   ├── fixtures/
│   ├── notebooks/
│   └── tests/
├── app_pages/
├── streamlit_app.py
├── tests/
│   ├── test_curriculum_manifest.py
│   ├── test_notebook_contracts.py
│   ├── test_docs_runtime_alignment.py
│   ├── test_security_invariants.py
│   └── test_live_contracts.py
├── docs/
│   ├── tdd-log.md
│   ├── live-smoke.md
│   ├── deployment-runbook.md
│   └── rollback.md
├── .github/workflows/ci.yml
├── Dockerfile
└── compose.yml
```

---

## 11. 필수 자동 검증 명령

프로젝트 생성 후 실제 Toolchain에 맞게 명령을 확정하되 최소 Gate는 다음과 같다.

```bash
uv sync --frozen
uv run pytest -q
uv run python -m compileall shared week1 week2 week3 app_pages streamlit_app.py
uv run python scripts/validate_notebooks.py
uv run python scripts/execute_notebooks.py
git diff --check
```

Container Artifact가 준비된 뒤에는 다음을 별도 검증한다.

```bash
docker compose config
docker compose build
docker compose up -d
# health와 API smoke readback
docker compose down
```

Docker·Compose를 사용할 수 없는 환경에서는 해당 Gate를 미검증으로 남긴다.

---

## 12. 최종 완료 정의

### Curriculum

- 기본 RAG 이후 공식 항목이 Manifest에서 App·Notebook·Test·Artifact에 연결된다.
- Week 1→3의 난이도 증가가 상태·권한·동시성·실패 복구·사람 승인·배포 책임으로 관찰된다.

### Project

- 독립 App 3개가 Fixture Mode에서 실행된다.
- FastAPI와 Streamlit의 실제 사용자 흐름이 Smoke Test된다.
- 실제 외부 Write는 없다.

### Notebook

- Week 1 5개, Week 2 5개, Week 3 6개 등 총 16개가 존재한다.
- 모든 Notebook이 App Import 없이 Top-to-bottom 실행된다.
- 정상·실패·중간 관찰·Assertion이 존재한다.

### Quality

- `uv sync --frozen` 통과
- 전체 Test Green
- Source Compile 통과
- Notebook Contract·Execution 통과
- Secret Scan 통과
- `git diff --check` 통과
- 독립 Review의 Security Concern·Logic Error 0건

### Live·Deployment

- Fixture·Mock·Live Evidence를 분리한다.
- OpenAI+pgvector·MCP·Container는 실제 Smoke를 실행한 경우에만 Verified로 표시한다.
- Health·Rollback 절차가 실행 가능한 문서로 존재한다.

---

## 13. 승인과 외부 변경 경계

이 `plan.md`의 작성은 다음 작업을 승인하지 않는다.

- Project 코드 생성
- Git 저장소 초기화·Commit·Push
- GitHub Remote·PR·Branch Protection 생성
- OpenAI 유료 호출
- Docker Service 기동
- 외부 MCP 연결
- 실제 기업 시스템·데이터 연동

구현 시작 전 다음을 별도로 승인한다.

1. 작업 경로 `/opt/data/agent-workflow-lab-v2`
2. 총 16개 Notebook 구성
3. Fixture 필수·Live 선택 검증 원칙
4. 실제 구현 시작

---

## 14. 참고 근거

- 한화내일아카데미 공식 기본 RAG 이후 커리큘럼
- 교육활용자료1의 3주 독립 Project·Notebook 계획
- `agent-workflow-lab` 2026-09-18 저장소 검증 기록
- 교육활용자료2 Project 주제 승인 및 커리큘럼·난이도 감사

핵심 적용 교훈은 다음과 같다.

```text
정본 고정
→ Contract Test RED
→ 완성 App GREEN
→ 독립 Notebook 작성·실행
→ Fixture Smoke
→ 선택적 Live Smoke
→ 독립 Review
→ 모든 Gate 재실행
```
