# 교육활용자료2 — Phase 0 실행 명세

- 상태: **승인 대기** (이 문서의 계획에 대한 실행 승인 전)
- 상위 계획: `docs/plan2.md`
- 설계 근거: `docs/plan2-vs-existing.md`
- 범위: plan2 §9 Phase 0 (Bootstrap + 정본 고정)에 한정. Week 1 앱 구현은 포함하지 않는다

---

## 1. 확정 파라미터

| 항목 | 확정값 | 근거 |
|---|---|---|
| 작업 경로 | `~/Desktop/project/hanhaw/agent-workflow-lab-v2` | plan2 §1의 `/opt/data`가 이 머신에 없다. `agent_ex1`·`hanwha_0902`가 있는 기존 프로젝트 홈이며 기존 저장소와 완전히 분리된다 |
| 주차 디렉터리 | `w1_retrieval_quality`<br>`w2_procurement_agent`<br>`w3_capa_control_tower` | **plan2 §10에서 의도적으로 벗어난다.** 두 과정이 모두 `week1~3`을 쓰면 "week2"가 출장비인지 구매 Agent인지 혼동된다 |
| 툴체인 | `brew install uv` + Python 3.14 | plan2 §9 Gate 0·§11 검증 명령을 수정 없이 쓰기 위해서다 |
| Git | **초기화하지 않는다** | plan2 §13이 별도 승인을 요구한다 |

### plan2와의 차이 기록

plan2 §10의 저장소 구조에서 `week1/`, `week2/`, `week3/`만 위 이름으로 바뀐다. 나머지 구조·파일명은 그대로 따른다. 이 차이는 새 저장소의 `README.md`와 `curriculum_manifest.yaml`에 함께 기록해, 계획서를 읽은 사람이 불일치로 오해하지 않게 한다.

---

## 2. 범위

### 포함

1. 툴체인 고정과 Gate 0 통과
2. 저장소 뼈대 (설정 파일, 빈 패키지 구조, README)
3. `curriculum_manifest.yaml`
4. `notebook_contracts.yaml`
5. RED 계약 테스트 5종
6. 각 계약 테스트의 변이 검사

### 제외 — plan2 §13이 별도 승인을 요구하는 것

앱 구현 · 노트북 작성 · `git init`·commit·push · GitHub remote·PR 생성 · OpenAI 유료 호출 · Docker Service 기동 · 외부 MCP 연결 · 실제 기업 시스템 연동

`brew install uv`는 예외로 승인되었다.

### 제외하는 이유

plan2 §2의 최우선 교훈 1번이 "기능 추가보다 먼저 정본과 계약을 고정한다"이고, Gate 1이 "App·README·Test·Notebook·Manifest가 모두 일치"를 요구한다. Manifest가 고정되기 전에 앱을 만들면 무엇에 맞출지가 정해지지 않은 상태로 구현하게 되어, 기존 저장소가 겪은 정본 불일치를 반복한다.

---

## 3. 디렉터리 구조 (Phase 0 종료 시점)

```text
agent-workflow-lab-v2/
├── README.md                      # 선행 과정 안내, 디렉터리 네이밍이 plan2 §10과 다른 이유
├── curriculum_manifest.yaml       # 정본 1
├── notebook_contracts.yaml        # 정본 2
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── shared/
│   ├── __init__.py
│   ├── contracts/__init__.py
│   ├── evaluation/__init__.py
│   ├── retrieval/__init__.py
│   ├── mcp/__init__.py
│   └── testing/__init__.py
├── tests/
│   ├── __init__.py
│   ├── test_curriculum_manifest.py
│   ├── test_notebook_contracts.py
│   ├── test_capability_qualification.py
│   ├── test_notebook_inventory.py
│   └── test_docs_runtime_alignment.py
└── docs/
    └── tdd-log.md                 # Phase 1부터 기록 시작
```

`w1_*`, `w2_*`, `w3_*` 디렉터리와 `app_pages/`, `streamlit_app.py`, `.github/`, `Dockerfile`, `compose.yml`은 **Phase 0에서 만들지 않는다.** manifest가 이들의 존재를 선언하고, 계약 테스트가 부재를 RED로 보고하는 것이 Phase 0의 정상 상태다.

---

## 4. `curriculum_manifest.yaml` 스키마

### 최상위

| 필드 | 설명 |
|---|---|
| `version` | 스키마 버전 (정수) |
| `course` | 과정 ID·제목·선행 과정 |
| `python` | 고정 Python 버전 |
| `naming_deviation` | plan2 §10과 다른 점과 이유 |
| `safety_invariants` | 전 주차 공통 안전 불변조건 |
| `capabilities` | Capability별 **이름을 쓸 자격 조건** |
| `projects` | 주차별 Project 3개 |

### `projects[]` 필드

| 필드 | 설명 |
|---|---|
| `id` | 디렉터리명과 동일 (`w1_retrieval_quality`) |
| `week`, `difficulty` | 주차 번호, 난이도 n/5 |
| `title`, `domain` | 제목, 도메인 식별자 |
| `user_problem`, `user_outputs` | 현업 문제와 사용자 결과물 |
| `endpoints[]` | method·path·request model·response model |
| `capabilities[]` | 이 Project가 **선언**하는 Capability. `capabilities` 최상위 항목을 참조 |
| `new_concepts[]` | 이번 주 신규 학습 개념 |
| `reused_not_reexplained[]` | 재사용하지만 재설명하지 않는 개념 |
| `notebooks[]` | Notebook Inventory (파일명 순서 포함) |
| `tests[]` | Test 파일 경로 |
| `safety_invariants[]` | 이 주차 고유 불변조건 |
| `completion.fixture[]` / `completion.live[]` | Fixture·Live 완료 기준 |

### 예시 (일부)

```yaml
version: 1
course:
  id: agent-workflow-lab-v2
  title: 기본 RAG 이후 — Advanced RAG · Tool Agent · Multi-Agent Delivery
  prerequisite:
    repository: agent-workflow-lab
    assumed_concepts: [기본 RAG, citation, evidence gate, structured output,
                       metadata filter, conditional routing, bounded loop]
python: "3.14"
audience:
  assumed: [Python 기본 문법, 함수·클래스·dict·list, 터미널 명령 실행]
  not_assumed: [RAG, LangChain, LangGraph, FastAPI, Streamlit]
naming_deviation:
  plan_section: "plan2 §10"
  changed: "week1/week2/week3 → w1_retrieval_quality/w2_procurement_agent/w3_capa_control_tower"
  reason: "선행 과정과 주차 번호가 겹쳐 도메인으로 구분한다"

safety_invariants:
  - synthetic_fixtures_only
  - no_real_credentials
  - no_external_write_tool
  - executed_actions_always_empty

capabilities:
  advanced_retrieval:
    qualifies_when:
      - baseline_and_advanced_compared_on_same_evaluation_set
      - recall_at_k_and_mrr_reported
  function_calling:
    qualifies_when:
      - tool_schema_declared
      - arguments_validated_before_dispatch
      - deterministic_dispatcher_present
      - observation_fed_back_into_next_turn
  mcp:
    qualifies_when:
      - server_runs_in_separate_process
      - client_discovers_resources_and_tools
  human_in_the_loop:
    qualifies_when:
      - execution_interrupts
      - state_persisted_with_thread_id
      - resumes_on_same_thread
      - approve_reject_edit_each_have_a_resume_path
  multi_agent:
    qualifies_when:
      - per_agent_input_output_contract
      - state_ownership_declared_and_enforced
      - handoff_explicit
      - single_worker_failure_isolated

projects:
  - id: w1_retrieval_quality
    week: 1
    difficulty: 1
    title: 기술지원 지식 검색 품질 개선 서비스
    domain: technical_support_knowledge_search
    capabilities: [advanced_retrieval]
    endpoints:
      - {method: POST, path: /diagnose,   request: DiagnoseRequest,  response: DiagnoseResponse}
      - {method: POST, path: /evaluate,   request: EvaluateRequest,  response: EvaluateResponse}
      - {method: GET,  path: /diagnostics}
    new_concepts: [고정 평가셋, Recall@k, MRR, Query Rewriting, Multi-Query,
                   Hybrid Retrieval, RRF, Parent Document Retriever,
                   Self-RAG Quality Gate, Bounded Retry, Abstain]
    reused_not_reexplained: [Document, splitter, citation, evidence gate]
    notebooks:                       # 순서·notebook_type은 notebook_contracts.yaml과 대조된다
      - {file: 01_evaluation_set_and_gold_evidence.ipynb, type: agent_technique}
      - {file: 02_recall_at_k.ipynb,                      type: agent_technique}
      - {file: 03_mrr.ipynb,                              type: agent_technique}
      - {file: 04_query_rewriting.ipynb,                  type: agent_technique}
      - {file: 05_multi_query_and_dedupe.ipynb,           type: agent_technique}
      - {file: 06_bm25_keyword_retrieval.ipynb,           type: agent_technique}
      - {file: 07_reciprocal_rank_fusion.ipynb,           type: agent_technique}
      - {file: 08_parent_document_retrieval.ipynb,        type: agent_technique}
      - {file: 09_relevance_and_grounding_grade.ipynb,    type: agent_technique}
      - {file: 10_end_to_end_retrieval_evaluation.ipynb,  type: agent_technique, integration: true}
    completion:
      fixture:
        - 동일 평가셋으로 Baseline과 Advanced 결과를 비교한다
        - 지원·모호·미지원 질문이 다른 Trace를 만든다
        - Citation이 실제 Parent·Source와 일치한다
        - 최대 재검색 횟수 후 안전하게 종료한다
```

---

## 5. `notebook_contracts.yaml` 스키마

### `common`

| 필드 | 값 |
|---|---|
| `required_headings` | 현업 시나리오 / 학습 목표 / 직접 조립 / 중간 결과 / 실패 경계 / 실제 app 연결 |
| `forbidden_imports` | 각 Project의 `app`, `domain` 모듈 |
| `forbidden_calls` | `create_app`, `run_*`, `build_*` 등 완성 Workflow 진입점 |
| `min_markdown_cells` / `min_code_cells` | 3 / 3 |
| `fixture_prefixes` | `practice_`, `mini_`, `sample_` |
| `require_assertion` | true |
| `require_success_and_failure_fixture` | true |
| `max_new_concepts_per_notebook` | 1 |

### `notebooks[]` 필드

| 필드 | 설명 |
|---|---|
| `file` | Project 기준 상대 경로 |
| `project`, `order` | 소속 Project ID, 순서 |
| `objective` | 학습 목표 |
| `primitives[]` | **직접 생성해야 할** Library Primitive |
| `fixtures.success` / `fixtures.failure` | 실행해야 할 정상·실패 Fixture |
| `observe[]` | 관찰해야 할 중간값 |
| `assertions[]` | 고정할 Assertion |
| `app_link` | 실제 App의 어느 흐름으로 확장되는지 |

### 예시 (1개)

```yaml
version: 1
common:
  required_headings: [현업 시나리오, 학습 목표, 직접 조립, 중간 결과, 실패 경계, 실제 app 연결]
  min_markdown_cells: 3
  min_code_cells: 3
  fixture_prefixes: [practice_, mini_, sample_]
  require_assertion: true
  require_success_and_failure_fixture: true
  forbidden_calls: [create_app, run_diagnose, run_evaluate, build_workflow, build_graph]
  audience_ref: curriculum_manifest.yaml#audience   # 학습 목표가 not_assumed 범위를 벗어나면 실패

notebooks:
  - file: w1_retrieval_quality/notebooks/07_reciprocal_rank_fusion.ipynb
    project: w1_retrieval_quality
    order: 7
    notebook_type: agent_technique
    new_concepts: [reciprocal_rank_fusion]        # 정확히 1개여야 한다
    objective: BM25와 Dense 검색 결과를 RRF로 합치고 단일 전략 대비 순위 변화를 관찰한다
    primitives: ["BM25", "cosine_similarity", "reciprocal_rank_fusion"]
    fixtures:
      success: 표현이 다른 질의가 Dense에서는 놓치고 BM25에서는 잡히는 문서 집합
      failure: 두 검색 모두 근거를 찾지 못해 융합 결과가 비는 질의
    observe: [각 전략의 순위, RRF 점수, 최종 순위 변화]
    assertions:
      - RRF 결과가 단일 전략보다 Gold 문서를 상위에 올린다
      - 두 전략 모두 비면 융합 결과도 빈 목록이다
    app_link: w1_retrieval_quality App의 Hybrid Retrieval·Fusion 단계
```

### Notebook 분류 축 — `notebook_type`

plan2 §6의 W3 노트북 6개 중 2개는 에이전트 기법이 아니라 개발 방법론이다. 같은 축으로 세면 "첫 주에 노트북이 가장 많다"는 누적 구조의 원칙이 깨져 보인다. `notebook_type`으로 축을 나눈다.

| 값 | 의미 |
|---|---|
| `agent_technique` | 그 주차 Project가 쓰는 에이전트·검색 기법. 주차별 개수가 감소해야 한다 |
| `engineering_practice` | 과정 전체에 적용되는 개발 방법론. 주차별 감소 규칙의 대상이 아니다 |

### 누적 구조 — 감소는 규칙이 아니라 결과다

강제해야 할 규칙은 **"이전 주차에서 실습한 기법을 다시 실습하지 않는다"** 하나다. 그러면 주차별로 도입 가능한 기법의 풀이 단조 감소한다.

```text
W1 풀 = 이 과정이 가르칠 전체 기법
W2 풀 = 전체 − W1에서 실습한 것
W3 풀 = 전체 − (W1 ∪ W2)에서 실습한 것
```

노트북 수가 줄어드는 것은 이 풀이 줄어든 **결과**다. 목표가 아니다.

**따라서 개수는 assert하지 않는다.** 개수를 못 박으면 어떤 주차가 실제로 더 많은 신규 기법을 필요로 할 때 커리큘럼을 왜곡해 개수를 맞추게 된다. 계약 테스트는 원인(중복 도입)을 검사하고, 개수는 **리포트만** 한다. 감소하지 않으면 실패가 아니라 경고로 표시해 설계 검토를 유도한다.

| Project | `agent_technique` | `engineering_practice` | 합계 |
|---|---:|---:|---:|
| `w1_retrieval_quality` | 6 | 0 | 6 |
| `w2_procurement_agent` | 5 | 0 | 5 |
| `w3_capa_control_tower` | 4 | 2 | 6 |
| 합계 | 15 | 2 | **17** |

위 6/5/4는 중복 도입 금지를 적용한 뒤 **관측된 값**이지 설계 목표가 아니다.

### 이 과정의 W1은 진짜 첫 주가 아니다

`docs/plan2-vs-existing.md` §4가 기록하듯 이 과정은 선행 과정을 전제한다. 기반 풀(Document·splitter·citation·evidence gate·structured output·metadata filter·conditional routing)은 **선행 과정이 이미 소진했다.** 따라서 이 과정의 W1 풀은 "전체 기법"이 아니라 "전체 − 선행 과정"이고, 곡선이 선행 과정(5/4/4)보다 평평한 것은 정상이다.

중복 도입 금지는 **과정 경계를 넘어서도 적용된다.** `reused_not_reexplained`에 선행 과정의 개념을 적고, 계약 테스트가 그 목록의 기법을 이 과정의 `new_concepts`에서 금지한다.

### 점검으로 반영한 변경 — plan2 초안 §4~6 대비

초안의 Notebook 16개를 아래 두 기준으로 점검해 29개로 조정했다. 파일명은 모두 최종 Inventory 기준이다.

#### (가) 누락 — 계획이 약속했으나 담당 Notebook이 없던 것

| # | 갭 | 조치 |
|---|---|---|
| 1 | W1에 Baseline↔Advanced를 같은 평가셋으로 비교하는 통합 자리가 없음 | `10_end_to_end_retrieval_evaluation.ipynb` **신규** |
| 2 | "Bounded Retry와 Abstain"이 어느 Notebook에도 배치되지 않음 | 위 신규 Notebook에 귀속 |
| 3 | Step Budget 귀속 불명 | W2 `05_step_budget.ipynb` **독립 분리** |
| 4 | Tool Idempotency 미배치 | W3 `06_resume_and_idempotency.ipynb`에 귀속 |
| 5 | W3에 전역 실패 불변조건을 고정할 자리가 없음 | `08_global_safety_invariants.ipynb` **신규 통합 Notebook** |
| 6 | GitHub PR·CI, Container·Health·Rollback이 Notebook 없이 "주요 기술"에 등재 | Notebook 약속에서 제거하고 `deliverables`(artifact)로 재분류 |
| 7 | W2 `04_chaining_routing_parallel`의 routing이 선행 과정 재실습 | routing을 `reused_not_reexplained`로 이동, chaining은 `04_action_observation_loop`에 흡수, 남은 fan-out만 `08_parallel_fanout_reduce.ipynb` |

#### (나) 과밀 — 한 Notebook에 도메인 개념이 2개 이상이던 것

| 초안 Notebook | 개념 수 | 분할 결과 |
|---|---:|---|
| `01_retrieval_evaluation_baseline` | 3 | `01_evaluation_set_and_gold_evidence` / `02_recall_at_k` / `03_mrr` |
| `02_query_rewriting_multi_query` | 2 | `04_query_rewriting` / `05_multi_query_and_dedupe` |
| `03_hybrid_retrieval_fusion` | 2 | `06_bm25_keyword_retrieval` / `07_reciprocal_rank_fusion` |
| `05_self_rag_quality_gate` | 2 | `09_relevance_and_grounding_grade` (관련도·근거 판정을 나란히 비교해야 차이가 드러나므로 유지) |
| `01_function_calling_tool_schema` | 2 | `01_tool_schema_declaration` / `02_tool_argument_validation` |
| `02_action_observation_dispatcher` | 3 | `03_deterministic_dispatcher` / `04_action_observation_loop` / `05_step_budget` |
| `03_local_mcp_resources_tools` | 2 | `06_mcp_server_and_client` / `07_mcp_resource_tool_discovery` |
| `01_agent_contracts_handoffs` | 2 | `01_agent_io_contract` / `02_state_ownership_and_handoff` |
| `02_supervisor_parallel_reducer` | 2 | `03_supervisor_worker` / `04_parallel_reducer_and_partial_failure` |
| `03_interrupt_checkpoint_resume` | 2 | `05_interrupt_and_checkpoint` / `06_resume_and_idempotency` |
| `04_mcp_permissions_audit` | 2 | `07_mcp_role_allowlist_and_audit` / `08_global_safety_invariants` |

### 학습자 전제 — 무엇을 알고 무엇을 모르는가

분할 기준을 정하려면 학습자의 출발선을 먼저 고정해야 한다. manifest의 `audience`에 기록한다.

| | 내용 |
|---|---|
| **안다고 가정** | Python 기본 문법, 함수·클래스·dict·list, 터미널에서 명령 실행 |
| **모른다고 가정** | RAG, LangChain, LangGraph, FastAPI 같은 백엔드, Streamlit 같은 프론트엔드 |

따라서 노트북은 **도메인 개념을 충분히 풀어서** 다루되, Python 문법 자체를 가르치지 않는다. `for` 문이나 `dict` 사용법을 설명하는 셀은 만들지 않는다.

### 분할 규칙 — 한 노트북 = 한 개념 + 한 시나리오

노트북 하나에 **도메인 개념을 2개 이상 넣지 않는다.** 2개면 노트북을 2개로 나눈다.

분할 대상은 위 `audience.not_assumed`의 개념 — RAG·LangChain·LangGraph·백엔드·프론트엔드 — 에 한정한다. **Python 문법은 분할 대상이 아니다.** `for` 문이나 `dict` 사용법을 설명하는 셀·노트북은 만들지 않는다.

#### 분할 예시 — `01_retrieval_evaluation_baseline`

| 분할 전 | 문제 |
|---|---|
| 평가셋 만들기 + Recall@k + MRR = 개념 3개 | 평가셋이 무엇인지 모르는 상태에서 지표 2개를 동시에 소화해야 한다 |

| 분할 후 | 그 노트북에서 배우는 것 하나 |
|---|---|
| `01_evaluation_set_and_gold_evidence` | 질문 5개를 정하고 각 질문의 정답 문서를 사람이 직접 지정한다. 지표는 아직 나오지 않는다 |
| `02_recall_at_k` | "검색 결과 3개 중 정답이 몇 개인가"를 손으로 세어본 뒤 함수로 만든다 |
| `03_mrr` | "정답이 몇 번째에 나왔나"를 점수로 바꾼다. 같은 데이터로 Recall@k와 무엇이 다른지 비교한다 |

### Notebook Inventory (총 29개)

주차별 마지막 `agent_technique` 노트북은 **통합·평가 역할**이며, 라이브러리 import 없이 순수 Python으로 축소 pipeline과 불변조건만 고정한다.

#### `w1_retrieval_quality` — 10개

| 순서 | 파일 | 이 노트북의 개념 하나 | 통합 |
|---:|---|---|:-:|
| 1 | `01_evaluation_set_and_gold_evidence.ipynb` | 평가셋과 정답 문서를 사람이 지정한다 | |
| 2 | `02_recall_at_k.ipynb` | 상위 k개 안에 정답이 들어왔는가 | |
| 3 | `03_mrr.ipynb` | 정답이 몇 번째에 나왔는가 | |
| 4 | `04_query_rewriting.ipynb` | 질문을 바꿔 쓰면 검색 결과가 달라진다 | |
| 5 | `05_multi_query_and_dedupe.ipynb` | 여러 질문으로 검색하고 중복을 제거한다 | |
| 6 | `06_bm25_keyword_retrieval.ipynb` | 키워드 검색은 임베딩 검색과 무엇이 다른가 | |
| 7 | `07_reciprocal_rank_fusion.ipynb` | 두 검색 결과의 순위를 하나로 합친다 | |
| 8 | `08_parent_document_retrieval.ipynb` | 작은 chunk로 찾고 큰 문맥으로 답한다 | |
| 9 | `09_relevance_and_grounding_grade.ipynb` | 검색 결과와 답변을 각각 판정한다 | |
| 10 | `10_end_to_end_retrieval_evaluation.ipynb` | Bounded Retry, Abstain, Baseline 대비 회귀 평가 | ● |

#### `w2_procurement_agent` — 9개

| 순서 | 파일 | 이 노트북의 개념 하나 | 통합 |
|---:|---|---|:-:|
| 1 | `01_tool_schema_declaration.ipynb` | Tool을 JSON Schema로 선언한다 | |
| 2 | `02_tool_argument_validation.ipynb` | 잘못된 인자를 실행 전에 막는다 | |
| 3 | `03_deterministic_dispatcher.ipynb` | 이름으로 Tool을 고르는 일은 모델이 아니라 코드가 한다 | |
| 4 | `04_action_observation_loop.ipynb` | Tool 결과를 다음 turn 입력으로 되돌린다 | |
| 5 | `05_step_budget.ipynb` | 몇 번 돌고 반드시 멈춘다 | |
| 6 | `06_mcp_server_and_client.ipynb` | 별도 Process의 MCP 서버에 붙는다 | |
| 7 | `07_mcp_resource_tool_discovery.ipynb` | 서버가 제공하는 Resource·Tool 목록을 읽는다 | |
| 8 | `08_parallel_fanout_reduce.ipynb` | 여러 Tool을 동시에 부르고 결과를 합친다 | |
| 9 | `09_tool_failure_matrix.ipynb` | Unknown Tool·Invalid Args·Timeout·Retry 소진 실패 행렬 | ● |

#### `w3_capa_control_tower` — 8 + 2개

| 순서 | 파일 | type | 이 노트북의 개념 하나 | 통합 |
|---:|---|---|---|:-:|
| 1 | `01_agent_io_contract.ipynb` | agent_technique | Agent의 입력과 출력을 계약으로 고정한다 | |
| 2 | `02_state_ownership_and_handoff.ipynb` | agent_technique | 누가 어떤 State를 쓸 수 있는가 | |
| 3 | `03_supervisor_worker.ipynb` | agent_technique | Supervisor가 Worker에게 일을 나눈다 | |
| 4 | `04_parallel_reducer_and_partial_failure.ipynb` | agent_technique | 병렬 결과를 합치고, 한 명이 실패해도 버틴다 | |
| 5 | `05_interrupt_and_checkpoint.ipynb` | agent_technique | 실행을 멈추고 상태를 저장한다 | |
| 6 | `06_resume_and_idempotency.ipynb` | agent_technique | 같은 Thread에서 재개하고, 끝난 Tool을 다시 부르지 않는다 | |
| 7 | `07_mcp_role_allowlist_and_audit.ipynb` | agent_technique | 역할별 권한과 감사 기록 | |
| 8 | `08_global_safety_invariants.ipynb` | agent_technique | 어떤 실패에서도 `executed_actions=[]` | ● |
| 9 | `09_tdd_skill_contracts.ipynb` | engineering_practice | RED→GREEN→REFACTOR, SDD Skill Contract | |
| 10 | `10_ports_adapters_contract_testing.ipynb` | engineering_practice | Clean Architecture, Ports/Adapters, Contract Test | |

#### 관측된 개수

| Project | `agent_technique` | `engineering_practice` |
|---|---:|---:|
| `w1_retrieval_quality` | 10 | 0 |
| `w2_procurement_agent` | 9 | 0 |
| `w3_capa_control_tower` | 8 | 2 |

10 > 9 > 8로 감소한다. **중복 도입 금지와 분할 규칙을 적용한 결과이지 설계 목표가 아니다.**

### 같은 문법의 재등장 — 기법과 시나리오가 모두 달라야 함

`docs/plan2-vs-existing.md` §1의 계승 규칙에 따라, 재등장하는 문법은 manifest에 아래처럼 기록하고 계약 테스트가 검사한다.

| 문법 | 재등장 | 각각의 신규 기법 |
|---|---|---|
| `StateGraph` | W2-04, W3-02, W3-03 | Fan-out·Reduce / Supervisor·Worker / Interrupt·Resume |
| Pydantic `BaseModel` | W2-01, W3-01 | Tool 인자 schema / Agent 입출력 Contract |
| MCP | W2-03, W3-04 | Discovery / Role Allowlist·Audit |

### 노트북 작성 시점

plan2 §2 교훈 3번에 따라 **각 주차 App이 GREEN이 된 뒤** 그 주차 노트북을 작성한다. Phase 0에서는 `notebook_contracts.yaml`에 계약만 선언하고 `.ipynb` 파일은 만들지 않는다. 따라서 Inventory 검사는 Phase 0에서 RED다.

## 6. RED 계약 테스트 5종

plan2 §9 Phase 0 5번("Manifest Contract Test를 먼저 RED로 만든다")에 해당한다. **Phase 0 종료 시점에 어떤 테스트가 GREEN이고 어떤 것이 RED인지를 미리 선언한다.** 전부 RED여야 하는 것이 아니라, 정본 자체의 정합성은 통과하고 구현 부재만 실패하는 것이 정상이다.

| # | 테스트 | 검사 내용 | Phase 0 기대 상태 |
|---|---|---|---|
| 1 | `test_curriculum_manifest.py` | manifest가 스키마를 만족하는가 — 필수 필드, 난이도 1~3 유일, Project ID 중복 없음, Endpoint 경로 중복 없음, `capabilities[]`가 최상위 정의를 참조하는가 | **GREEN** |
| 2 | `test_notebook_contracts.py` | contracts의 노트북 목록이 manifest Inventory와 **정확히 일치**하는가, 각 항목에 필수 필드가 있는가, `primitives`·`assertions`가 비어 있지 않은가 | **GREEN** |
| 2b | `test_cumulative_structure.py` | **어떤 기법도 두 주차의 `new_concepts`에 동시에 나타나지 않는가**, 선행 과정의 `reused_not_reexplained` 항목이 `new_concepts`에 없는가, 모든 노트북이 이전 주차에 없던 도메인 개념을 **정확히 1개** 도입하는가(2개 이상이면 분할 대상), 주차마다 통합 노트북이 정확히 1개인가, 재등장 문법의 기법·시나리오가 모두 다른가. **개수는 검사하지 않고 리포트만 한다** | **GREEN** |
| 3 | `test_notebook_inventory.py` | 파일시스템의 `*.ipynb` 집합 == manifest Inventory | **RED** (노트북 0개) |
| 4 | `test_capability_qualification.py` | Project가 선언한 Capability마다, 그 자격 조건을 만족하는 근거가 구현에 존재하는가 | **RED** (앱 없음) |
| 5 | `test_docs_runtime_alignment.py` | README·Endpoint·Model명·Test 파일 경로가 manifest와 일치하는가 | **RED** (앱·테스트 없음) |

### 왜 1·2는 GREEN이어야 하는가

정본이 스스로 모순되면 그 위의 모든 검사가 무의미하다. 1·2가 GREEN이라는 것은 "무엇을 만들지가 모순 없이 확정되었다"는 뜻이고, 3·4·5가 RED라는 것은 "아직 만들지 않았다"는 뜻이다. 이 구분이 Phase 0의 산출물이다.

### 변이 검사

기존 저장소에서 계약 테스트를 추가할 때 썼던 방식을 그대로 적용한다. 각 테스트마다 의도적으로 정본을 훼손하고 **실제로 실패하는지** 확인한 뒤 원복한다.

| 테스트 | 주입할 변이 | 기대 |
|---|---|---|
| 1 | 두 Project에 같은 `difficulty` 부여 | 실패 |
| 1 | 정의되지 않은 Capability 이름 참조 | 실패 |
| 2b | W1과 W2의 `new_concepts`에 같은 기법을 넣기 | 실패 (중복 도입) |
| 2b | 선행 과정 개념(예: conditional routing)을 `new_concepts`에 넣기 | 실패 (재설명 금지 위반) |
| 2b | 한 노트북의 `new_concepts`에 도메인 개념 2개 넣기 | 실패 (분할 규칙 위반) |
| 2b | `audience.not_assumed`에 없는 것(예: Python `for` 문)을 노트북 학습 목표로 넣기 | 실패 (범위 밖) |
| 2b | 어느 노트북의 신규 기법을 전부 이전 주차 것으로 교체 | 실패 (증가분 없음) |
| 2b | W2에 노트북 2개 추가해 6개로 만들기 | **통과** — 개수는 assert하지 않는다. 리포트에 경고만 표시 |
| 2b | 어느 주차의 통합 노트북 표시를 제거 | 실패 |
| 2 | manifest Inventory에서 노트북 1개 삭제 | 실패 (contracts와 불일치) |
| 3 | 빈 `.ipynb` 1개 생성 | 실패 메시지가 그 파일을 지목 |
| 4 | Capability 자격 조건 1개 제거 | 해당 조건이 더는 요구되지 않음을 확인 |
| 5 | manifest의 Endpoint 경로 변경 | 실패 |

---

## 7. 실행 순서와 명령

```bash
# 1. 툴체인
brew install uv
uv --version

# 2. 경로와 뼈대
mkdir -p ~/Desktop/project/hanhaw/agent-workflow-lab-v2
# pyproject.toml, .gitignore, .env.example, README.md 작성
# shared/{contracts,evaluation,retrieval,mcp,testing}/__init__.py 생성

# 3. 정본 2종 작성
#    curriculum_manifest.yaml, notebook_contracts.yaml

# 4. 계약 테스트 5종 작성

# 5. Gate 0
uv sync --frozen
uv run pytest -q          # 1·2 GREEN, 3·4·5 RED 확인

# 6. 변이 검사 6건 수행 후 원복

# 7. 결과 보고
```

Phase 0의 의존성은 최소로 고정한다 — `pyyaml`, `pytest`. 검색·MCP·checkpoint 관련 패키지는 해당 Phase에서 추가한다. Phase 0에서 미리 넣으면 Gate 0이 무엇을 보증하는지 흐려진다.

---

## 8. Phase 0 완료 정의

| 항목 | 기준 |
|---|---|
| Gate 0 | 빈 환경에서 `uv sync --frozen` 통과 |
| 정본 정합성 | 계약 테스트 1·2 GREEN |
| 구현 부재 보고 | 계약 테스트 3·4·5가 **의도한 이유로** RED, 실패 메시지가 누락 대상을 지목 |
| 변이 검사 | 6건 모두 기대대로 실패 후 원복 |
| 문서 | README에 선행 과정과 네이밍 차이 기록 |
| 경계 준수 | `git init` 없음, 앱·노트북 파일 없음, 외부 호출 없음 |

---

## 9. Phase 1 진입 조건

Phase 0 완료 정의를 모두 충족하고, **별도 승인**을 받은 뒤 Week 1 앱 구현을 시작한다. 승인 시 함께 정할 사항:

1. Week 1 평가셋의 크기와 Gold Evidence 작성 방식
2. 합성 지식 문서(기술지원 매뉴얼·FAQ·Troubleshooting)의 분량과 카테고리 구성
3. Baseline 대비 개선을 어느 지표로 보고할지 (Recall@k의 k, MRR 기준)
4. TDD 로그(`docs/tdd-log.md`) 기록 수준

---

## 10. 이 문서의 위치

이 문서는 기존 저장소 `agent-workflow-lab`의 `docs/`에 둔다. 새 저장소가 아직 없기 때문이며, Phase 0 실행 시 새 저장소로 복사해 `docs/phase0-execution.md`로 남긴다. 두 저장소를 잇는 결정 기록은 `docs/plan2-vs-existing.md`가 담당한다.
