# 교육활용자료2 계획 vs 기존 `agent-workflow-lab` — 무엇을 계승하고 무엇을 끊는가

- 작성 목적: 새 저장소 Phase 0에서 `curriculum_manifest.yaml`을 설계할 때의 입력
- 비교 대상: 이 저장소의 현재 상태(`db65469`)와 `docs/plan2.md`
- 판단 결론: **새 폴더에서 시작한다.** 근거는 §6

---

## 1. 계승하는 것 — 교수법의 DNA

plan2는 새 교육 방식을 발명한 것이 아니라, 이 저장소가 암묵적으로 지켜온 규칙을 문서로 명문화한 것이다.

| 원칙 | 기존 저장소 | plan2 |
|---|---|---|
| Project와 Notebook의 역할 분리 | "app 함수를 호출하지 않고 primitive를 직접 조립" (README) | "Notebook은 완성 App을 호출하는 사용 데모가 아니다" (§1) |
| app import 금지 | 문자열 + AST 이중 차단 | AST 기반 금지 Import·Call 검사 (§2) |
| 이전 주차 재설명 금지 | 개념 진행표 `도입 / 재사용 / 범위 밖` | "이전 주 개념은 재설명하지 않고 신규 사용 패턴에 집중" (§7) |
| 노트북 내부 순서 | 시나리오 → 직접 조립 → 중간 결과 → 실패 경계 → app 연결 | §7이 같은 순서를 그대로 재기술 |
| 합성 데이터·읽기 전용 | NoriWorks 가상 문서, 실제 승인·실행 없음 | 합성 Fixture, 구매·결제·QMS/MES·Shell 실행 없음 (§1) |
| fixture 기본 / live 선택 | `APP_MODE`, 응답의 `mode` 키로 증거 구분 | "Fixture·Mock·Live를 서로 다른 증거로 보고" (§1) |
| 주차당 독립 Project + 난이도 상승 | 1/5 → 2/5 → 3/5 | 1/5 → 2/5 → 3/5 |

**따라서 노트북 계약, Project/Notebook 분리, fixture 기본값은 재설계 대상이 아니라 이식 대상이다.**

---

## 2. 달라지는 것 — 평가 기준이 한 단계 올라간다

| 축 | 기존 | plan2 |
|---|---|---|
| 난이도를 만드는 것 | 같은 라이브러리의 다른 사용 패턴 (선형 edge → 조건부 → bounded loop) | 상태·권한·동시성·실패 복구·사람 승인·배포 책임 (§12) |
| RAG 수준 | 단일 dense 검색 + 관련도 임계값 | Advanced RAG (rewriting, multi-query, hybrid, RRF, parent doc, self-RAG) |
| 검색 품질 측정 | 없음 | 고정 평가셋·Gold Evidence·Recall@k·MRR, Baseline 대비 비교가 완료 기준 |
| Tool 사용 | 명령 문자열 allowlist | JSON Schema Function Calling + Dispatcher + Observation Loop + MCP |
| HITL | 승인 packet 생성까지 | Interrupt·Checkpoint·Thread Resume, Approve/Reject/Edit 후 재개 |
| Multi-Agent | 순차 node에 역할 이름 부여 | Supervisor·Worker, Parallel Reducer, Partial Failure Isolation |
| 정본 관리 | 테스트 파일 안의 Python dict | `curriculum_manifest.yaml` + `notebook_contracts.yaml` |
| 개발 방식 | 사후 테스트 | RED → GREEN → REFACTOR 강제 + `docs/tdd-log.md` (§8) |
| 노트북 실행 검증 | 13개 중 2개만 `exec` | 16개 전부 `nbclient` top-to-bottom |
| 배포 | artifact만 존재, README가 "미검증" 자인 | Build·Health·Smoke를 실행해야 `verified` (Gate 4) |
| 품질 게이트 | 작성자 자체 확인 | 독립 Reviewer, Security/Logic 이슈 0건까지 Release 불가 (Phase 5) |
| 도메인 | 단일 가상기업 NoriWorks 사내 관리 업무 | 기술지원·구매·제조 CAPA, 서로 독립 |
| 노트북 수 | 13 (5+4+4) | 16 (5+5+6) |

---

## 3. 검증된 지적 — plan2 §2의 마지막 3건은 "과대표기"다

plan2 §2 표의 대부분은 버그·불일치 지적이지만, 아래 3건은 성격이 다르다. **기능이 없는데 이름을 붙였다**는 지적이고, 현재 코드에서 사실로 확인된다.

| plan2의 지적 | 코드 확인 결과 |
|---|---|
| "Review Packet을 실제 HITL로 표현" | `checkpoint` / `interrupt` / `resume` / `thread_id` **0건**. 승인 packet을 만들 뿐 실행 중단·상태 저장·재개가 없다 |
| "Command 문자열 검사를 Function Calling으로 표현" | `bind_tools` / `tool_calls` / `@tool` / `ToolNode` **0건**. Tool schema도 dispatcher도 observation 환류도 없다 |
| "역할 이름이 다른 Node를 완전한 Multi-Agent로 표현" | app에 ownership 강제 **0건**. `apply_owned_update`는 `week3/notebooks/01`에만 있고 `week3/app.py`에는 없다 |

즉 기존 Week 3은 **"멀티에이전트 HITL 시스템"이 아니라 "순차 node + 결정론적 문자열 가드 + 승인 packet 생성"** 이다. 교육 자료로는 유효하지만 이름값은 못 했다.

> 이 세 줄이 새 저장소 설계에 주는 요구사항은 §5에 정리했다.

---

## 4. 기존 3주가 plan2의 어디로 가는가

기존 과정은 폐기되는 것이 아니라 **선행 과정**이 된다.

```text
기존 W1 (기본 RAG·citation·evidence gate)   →  plan2 W1의 Baseline
                                                그 위에 rewriting·hybrid·RRF·parent·self-RAG를 쌓는다

기존 W2 (structured output·filter·routing)  →  plan2 W2의 선행 조건 (classify·plan·routing)

기존 W3 (allowlist·bounded loop·packet)     →  분화·승격
                                                ├→ plan2 W2: 진짜 Tool safety (schema·dispatcher·fail-closed)
                                                └→ plan2 W3: 진짜 HITL (interrupt·checkpoint·resume)
```

새 저장소 README는 이 관계를 명시해 학습자가 선행 과정을 먼저 듣도록 안내한다.

---

## 5. Manifest 설계에 반영할 것 — 용어 자격 조건

§3의 과대표기를 구조적으로 막으려면, manifest에 기능 목록만 적어서는 부족하다. **그 이름을 쓸 자격 조건**을 함께 적고 테스트로 강제한다.

| 선언할 Capability | 이 이름을 쓸 자격 조건 (전부 충족해야 함) |
|---|---|
| `function_calling` | Tool schema 선언 + 인자 검증 + Deterministic Dispatcher + Observation이 다음 turn 입력으로 환류 |
| `mcp` | 별도 Process의 Server + Client Discovery + Resource·Tool 목록 조회 성공 |
| `human_in_the_loop` | 실행 중단 + 상태 저장 + 동일 Thread 재개 + Approve/Reject/Edit 각각의 재개 경로 |
| `multi_agent` | Agent별 Input·Output Contract + 소유 State 명시 + Handoff + 한 Worker 실패 시 격리 |
| `advanced_retrieval` | Baseline 대비 동일 평가셋에서의 지표 비교 결과가 존재 |

기존 저장소의 `APP_TECHNIQUE_COVERAGE` 테스트가 "노트북 기법이 app에 도달했는가"를 잡았듯, 새 저장소에서는 "선언한 Capability가 실제 구현에 도달했는가"를 같은 방식으로 잡는다.

---

## 6. 새 폴더로 가는 근거

이어 붙이지 않는 이유는 기능 추가량이 아니라 **기반 교체**이기 때문이다.

| plan2 요구 | 기존 상태 | 충돌 |
|---|---|---|
| `curriculum_manifest.yaml` 단일 정본 (§3) | 정본이 `tests/test_curriculum_contract.py`의 Python dict | 정본 2개 공존 → §2의 1번 예방 규칙을 첫날부터 위반 |
| `uv run pytest -q` (§11) | unittest 9개 파일, pytest 미설치 | Gate 명령이 갈라짐 |
| Fresh 환경 `uv sync --frozen`이 Gate 0 | uv 미설치, 2600줄 기존 lock | "깨끗한 환경에서 lockfile 생성" 요구가 무의미해짐 |
| 주차별 `domain.py` + `shared/{contracts,evaluation,retrieval,mcp,testing}/` | 단일 `app.py` + 평면 `shared/` | 한 저장소에 두 아키텍처 공존 |
| pytest·rank_bm25·mcp·langgraph-checkpoint·nbclient·pyyaml | 6개 모두 없음 | Week 1 수강생이 MCP·BM25·checkpointer까지 설치 |

여기에 더해 이 저장소에는 `docs/project-blueprint.md` §11.2의 미해결 부채(RAG 구현 2벌, compose 2벌, 앱을 못 담는 Dockerfile, UI의 서버 Pydantic 직접 import)가 남아 있다. plan2 §2는 바로 이런 부채의 재발 방지가 목적이므로, 그 위에 얹으면 위반 상태에서 출발한다.

plan2 자신도 별도 경로를 전제한다 — §1 대상 경로, §9 Phase 0 "새 독립 작업 경로를 만든다", §10 저장소 구조, §13 승인 항목 1번. 난이도도 1/5부터 다시 시작하므로 6주 연속 과정이 아니라 **독립된 두 번째 3주 과정**이다.

---

## 7. 이식 목록

### 가져갈 것

| 자산 | 새 위치 제안 | 상태 |
|---|---|---|
| `shared/live_rag.py`의 filter·structured output·diagnostics | `shared/retrieval/` 로 분해 | 실제 pgvector로 live 검증 완료 |
| `shared/ingest.py` + `카테고리:` 헤더 규약 | `shared/retrieval/ingest.py` | 검증 완료 |
| `ui_common.py`의 `render_result` / `render_rag_observability` 골격 | `app_pages/_common.py` | fixture smoke 통과 |
| 계약 테스트 **아이디어** (AST 금지 import, 필수 용어, 시나리오 고유성, 기법 커버리지) | manifest 기반으로 재구현 | 변이 검사로 유효성 확인 |
| 노트북 작성 패턴 (필수 헤딩 6개, `practice_` 접두, `assert` 마감) | `notebook_contracts.yaml` | 13개 노트북에서 검증 |
| `infra/compose.pgvector.yml` | `compose.yml` | 실제 기동·healthy 확인 |
| `docs/project-blueprint.md` | 설계 입력으로 참조 | — |

### 버릴 것

`lab_core.py` (중복 RAG 구현), 루트 `docker-compose.yml` (compose 2벌 문제), 현재 `Dockerfile` (`shared/`·`knowledge/`·`app_pages/`를 COPY하지 않아 기동 불가), `uv.lock` (깨끗한 환경에서 재생성), `labs/` (빈 잔재).

---

## 8. 한 줄 요약

기존 과정은 **라이브러리 사용법을 안전하게 가르치는 과정**이고, plan2는 **현업 시스템을 책임지고 만드는 과정**이다. 교수법은 그대로 물려받되, 평가 대상이 "기법을 썼는가"에서 **"그 이름을 쓸 자격이 있는가"** 로 올라간다.
