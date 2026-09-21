# 프로젝트 청사진 — 다른 주제로 동일 구조를 재생성하기 위한 명세

이 문서는 `agent-workflow-lab` 저장소를 역분석해 **무엇을 만든 프로젝트인지, 어떤 규칙을 고집하는지, 다른 주제로 복제할 때 무엇을 바꾸고 무엇을 그대로 두어야 하는지**를 정리한 것이다. 코드·테스트·문서를 실제로 읽어 확인한 내용만 담았고, 마지막 장에 **현재 저장소에 남아 있는 불일치(복제하면 안 되는 것)** 를 따로 모았다.

---

## 1. 이 프로젝트의 정체

| 항목 | 내용 |
|---|---|
| 한 줄 정의 | LangChain RAG + LangGraph 워크플로를 **3주 점진형 커리큘럼**으로 가르치는 실습 저장소 |
| 산출물 | 주차별 FastAPI 앱 3개 + 통합 Streamlit UI 1개 + 주차별 Jupyter 실습 노트북 + 자동 테스트 |
| 도메인 | 가상 B2B SaaS 기업 **NoriWorks**의 사내 정책 업무 (휴가 / 출장비 / IT 변경) |
| 학습자 | LangChain·LangGraph 초심자. Python은 읽을 줄 알지만 RAG·에이전트는 처음 |
| 실행 안전성 | **읽기 전용**. 실제 승인·환불·계정 변경·운영 명령을 절대 실행하지 않음 |
| 언어 | 코드 식별자·docstring은 영어, 학습자 대상 문서·UI·프롬프트 지시문은 한국어 |

### 설계 의도 (커밋 이력에서 확인됨)
1. "동작하는 데모"가 아니라 **설계대로 가르쳐지는지 CI로 강제되는 교재**
2. 근거 없이는 답하지 않는 **grounding 우선** RAG
3. API 키·DB 없이도 전 과정이 돌아가는 **fixture 기본값**
4. 초심자가 혼자 끝까지 실행할 수 있게 하는 **실행 안내 문서 세트**

---

## 2. 런타임 아키텍처 (고정)

```text
[적재 1회]
knowledge/<week>/*.md
  → shared/ingest.py (RecursiveCharacterTextSplitter 500/50)
  → OpenAI Embeddings
  → pgvector 테이블 agent_workflow_<week>

[질의 시]
브라우저 :8501
  → Streamlit (app_pages/<week>.py + ui_common.py)
  → HTTP  :8011 / :8012 / :8013        ← UI는 워크플로를 직접 import 하지 않는다
  → FastAPI (week<N>/app.py)
      → shared/live_rag.py : 질문 임베딩 → pgvector 유사도 검색 → 임계값 필터
      → LangGraph StateGraph 실행
      → 임계값 통과 청크만 LLM 근거로 전달
  → JSON (answer + citations + retrieval_trace)
  → Streamlit 렌더링
```

### 계층 경계 4원칙 — 절대 깨지 않음
1. **UI는 HTTP만 쓴다.** Streamlit이 `week1.app.run_query()`를 직접 부르지 않는다. 이 경계 자체가 수업 내용이다.
2. **UI는 DB·`.env`에 직접 접근하지 않는다.** 진단 정보도 API의 `GET /diagnostics`를 통해서만 읽는다.
3. **비밀값은 서버 프로세스 안에만 있다.** 응답·로그·화면 어디에도 전체 API 키, DB 연결 문자열, 임베딩 벡터 전문을 싣지 않는다. (키는 `앞 5자 + …`만)
4. **citation은 LLM이 만들지 않는다.** 실제 검색된 Document의 `document_id`/`chunk_id` 메타데이터에서 서버가 조립한다.

### 포트 규약
| 대상 | 포트 | 환경변수 오버라이드 |
|---|---|---|
| Week 1 API | 8011 `/query` | `WEEK1_API_URL` |
| Week 2 API | 8012 `/review` | `WEEK2_API_URL` |
| Week 3 API | 8013 `/review-change` | `WEEK3_API_URL` |
| Streamlit | 8501 | — |
| pgvector | 127.0.0.1:5432 (`infra/compose.pgvector.yml` 기준) | — |

DB 포트는 **반드시 `127.0.0.1:` 에 바인딩**한다. 외부 노출 금지.

---

## 3. 실행 모드 — fixture / live

`shared/live_rag.py::is_live_mode()` 한 곳에서만 판정한다 (`APP_MODE` 환경변수, 기본 `fixture`).

| | fixture (기본) | live (opt-in) |
|---|---|---|
| 필요 조건 | 없음 | `OPENAI_API_KEY` + `DATABASE_URL` |
| 검색 | 모듈 상수 `POLICY_CHUNKS` 토큰 매칭 | pgvector 유사도 검색 |
| 생성 | 검색된 청크 본문 그대로 | `generate_grounded_text()` (ChatOpenAI, temperature=0) |
| 결정성 | 완전 결정적 → 테스트·노트북이 여기에 의존 | 비결정적 |
| 진단 | `{"mode":"fixture", chunk_count:0}` | 실제 청크 수·모델·임계값 |

**핵심 규칙**
- live 의존성(`langchain_openai`, `langchain_postgres`)은 `_imports()` 안에서 **지연 import**. fixture 경로는 모듈을 import 해도 네트워크 클라이언트를 만들지 않는다.
- 모든 API 응답에 `"mode"` 키를 실어, fixture 결과를 live 실행 증거로 오인하지 못하게 한다.
- 오타는 조용히 폴백하지 않는다. `APP_MODE` 값이 `fixture`/`live`가 아니면 기동 단계에서 실패한다 (`lab_core.resolve_mode`).
- 설정 검증은 타입·범위까지: `RAG_RETRIEVAL_K ≥ 1`, `0 ≤ RAG_MIN_RELEVANCE ≤ 1`, `OPENAI_EMBEDDING_DIMENSIONS ≥ 1`.

---

## 4. API 계약 (주차 공통)

### 4.1 엔드포인트
| 메서드 | 경로 | 용도 |
|---|---|---|
| GET | `/` | 브라우저로 접속한 학습자를 위한 안내 JSON (404 방지) |
| GET | `/favicon.ico` | 204 (로그 노이즈 제거) |
| GET | `/health` | `status`, `difficulty`, `workflow_engine`, `live_mode` |
| GET | `/diagnostics?include_chunks=` | 읽기 전용 live RAG 연결 상태 |
| POST | 주차별 동사 경로 | 워크플로 실행 |

### 4.2 응답 공통 키 — 모든 주차가 동일하게 반환
```jsonc
{
  "difficulty": 1,                       // 주차 번호 = 난이도
  "mode": "fixture" | "live",
  "business_use_case": "hr_leave_policy_self_service",
  "workflow_engine": "langgraph",
  "agents_run": ["retriever", "answer", "evidence_guard"],  // 실행된 node 순서
  "status": "answered",
  "citations": [{"document_id": "...", "chunk_id": "..."}],
  "retrieval_trace": [{"document_id","chunk_id","relevance_score","selected"}]
}
```
주차별 확장 키만 추가한다.

| 주차 | 확장 키 |
|---|---|
| W1 | `answer`, `reason` |
| W2 | `category`, `priority`, `classification_reason`, `required_follow_up`, `review_summary` |
| W3 | `severity`, `revision_count`, `max_revisions`, `draft`, `approval_packet`, `observation_plan`, `executed_commands` |

`executed_commands`는 항상 `[]`다. 값이 아니라 **불변조건**이므로 응답에서 빼지 않는다 — 비어 있음을 매번 증명하는 것이 목적이다.

### 4.3 status 어휘 (UI가 3분류로 렌더링)
| 분류 | 값 | UI 표현 |
|---|---|---|
| 성공 | `answered`, `approved_for_next_step`, `done`, `plan_ready` | 초록 success |
| 사람 개입 | `clarify`, `manager_review`, `human_approval_required`, `blocked_manual_review`, `human_review` | 노랑 warning + "명령은 실행되지 않았습니다" |
| 근거 부족 | `insufficient_evidence` | 파랑 info |

### 4.4 오류 계약
live 관련 모든 실패는 `LiveRagError`로 좁혀서 잡고 **HTTP 503**으로 변환한다.
```python
raise HTTPException(status_code=503,
    detail={"code": "live_rag_unavailable", "message": str(error)})
```
메시지는 한국어 안내문이며 비밀값·스택을 포함하지 않는다.

---

## 5. LangGraph 코딩 규약

```python
class XxxState(TypedDict, total=False):
    ...도메인 필드...
    retrieval_trace: list[dict[str, str | float | bool]]
    citations: list[dict[str, str]]
    status: str
    agents_run: Annotated[list[str], operator.add]   # 누적 reducer

def xxx_node(state: XxxState) -> XxxState:
    # 자신이 소유한 필드 + agents_run 만 반환한다. 전체 state를 되돌려주지 않는다.
    return {"...": ..., "agents_run": ["xxx"]}

def build_graph():        # START → ... → END 를 명시적으로 연결
    ...
    return graph.compile()

WORKFLOW = build_graph()  # 모듈 로드 시 1회 컴파일

def run_xxx(payload) -> dict:   # API·테스트의 단일 canonical 진입점
    state = WORKFLOW.invoke({**payload.model_dump(), "agents_run": []})
    return { ...4.2의 공통 응답... }

def create_app() -> FastAPI:    # 팩토리. 모듈 끝에서 app = create_app()
```

### 난이도를 만드는 축 — 같은 라이브러리를 다르게 쓴다
| | Week 1 (1/5) | Week 2 (2/5) | Week 3 (3/5) |
|---|---|---|---|
| 그래프 형태 | 선형 `add_edge`만 | `add_conditional_edges` 1회 분기 | 이전 node로 돌아가는 **제한 loop** |
| 새 개념 | Pydantic 경계, Document/splitter, retrieval, citation, evidence gate | `Literal` structured output, `metadata_filter`, 다중 경로 평가 | state 소유권, `revision_count`/`MAX_REVISIONS`, 명령 allowlist, HITL packet, fail-closed |
| 안전 장치 | 근거 없으면 답하지 않음 | 결정론적 규칙(영수증 확인)은 LLM에 맡기지 않음 | 모델이 붙인 `dry_run` flag를 믿지 않고 별도 결정론 검사 |

**개념은 한 번만 가르친다.** Week 2·3 README에는 `## 선행 조건 — 반복 설명하지 않는 것` 절이 있어 이전 주차 개념을 재강의하지 않는다고 명시한다. 루트 README의 "개념 진행표"가 `도입·실습 / 재사용 / 범위 밖` 3값으로 이를 표로 고정한다.

---

## 6. 지식 문서(knowledge/) 규약

```
knowledge/
  README.md              ← "가상 기업의 실습용 문서이며 실제 업무 판단에 쓰지 말 것" 고지 필수
  week1/*.md  week2/*.md  week3/*.md
```

- 주차당 **정책 문서 1개 + 보조 문서(체크리스트/템플릿/가이드) 1개** 구성.
- 문서들은 서로 모순되지 않게 작성하고, 각 주차 API의 입력값·안전 규칙 범위 안으로 내용을 제한한다.
- 메타데이터 규약: `document_id` = 파일 stem, `chunk_id` = `<stem>-001` 형식 3자리, `source` = knowledge 기준 상대경로, `week`, `category`.
- `category`는 Markdown 본문의 `카테고리: <값>` 헤더 한 줄에서 읽는다 (`shared/ingest.py::document_category`). 헤더가 없으면 **조용히 검색 대상에 섞이지 않도록** catch-all인 `other`로 떨어진다. 이 필드가 Week 2의 `metadata_filter` 대상이다.
- 필터가 의미를 가지려면 **분류 enum의 모든 값에 문서가 존재해야 한다.** 값 하나가 비면 그 분류는 항상 `insufficient_evidence`로 끝난다.
- 벡터 ID는 `uuid5(NAMESPACE_URL, "<table>:<document_id>:<chunk_id>:<본문>")` — **결정적**이므로 재적재가 upsert가 된다.
- `--reset`은 테이블을 삭제·재생성하므로 임베딩 모델/차원 변경 같은 의도적 초기화에만 쓴다.
- 적재 CLI는 `APP_MODE != live`면 즉시 에러로 거부한다.

---

## 7. 노트북 — 역할 분담과 규격

### 7.0 폴더의 역할
`week<N>/notebooks/`는 **완성된 `app.py`를 분해해 최소 크기로 다시 조립해 보는 해부 실습실**이다. app이 완성품이라면 노트북은 그 안에 들어간 primitive를 하나씩 떼어낸 것이다. 그래서 계약 테스트가 app import를 AST로 차단한다 — 완성품을 호출하면 해부가 아니라 사용이 된다.

공통 규칙
- **번호 = 파이프라인 순서**: 입력 검증 → 문서화/분할 → 검색 → 그래프 → API·평가
- **주차의 마지막 노트북은 통합·평가 담당**, 나머지는 단일 primitive 분해 담당
- 각 노트북은 `실제 app 연결` 절에서 "이 조각이 app의 어디인가"를 되짚고, `다음 Notebook 연결` 절에서 다음 조각으로 넘긴다
- 축소 모델의 한계를 숨기지 않는다 (예: `week2/02`는 "lexical/embedding relevance 판정까지 충분히 구현한 검색기는 아니다"라고 명시)
- 개수는 누적 구조를 따른다: **Week 1은 5개, Week 2·3은 4개**. Week 1이 FastAPI 경계를 이미 가르쳤으므로 Week 2·3에는 API 노트북이 없다.

### 7.0.1 Week 1 — 파이프라인을 앞에서 뒤로 한 조각씩

| 파일 | 역할 | 사용 라이브러리 / 정의 심볼 | 고정하는 계약 |
|---|---|---|---|
| `01_request_response_models` | 입구 방어막. 빈·짧은 질문을 검색 **전에** 거부 | Pydantic / `PracticeQuery`, `PracticeResponse` | `ValidationError`의 `type`·`loc` 구조. 실패 입력을 기본 질문으로 몰래 바꾸지 않음 |
| `02_documents_and_splitting` | 검색 단위 만들기. 분할 후에도 원문 metadata가 살아남는가 | `Document`, `RecursiveCharacterTextSplitter` | chunk 수 증가 + `document_id` 집합 보존 |
| `03_embeddings_pgvector_retrieval` | 검색의 심장. 임베딩·코사인·top-k·**임계값** | 표준 라이브러리만 / `MiniEmbedding`, `cosine_similarity`, `practice_search` | 임계값 미달은 빈 목록. top-k가 돌려줬다고 근거로 인정하지 않음 |
| `04_linear_stategraph` | 그래프 문법. state·node·edge·invoke | `TypedDict`, `StateGraph` (**`add_edge`만**) | `steps == ["retrieve","answer"]`. node가 이전 state를 지우지 않음 |
| `05_grounded_api_testing` | **1주차 통합**. 앞 4개를 FastAPI 경계 + evidence gate에 결합 | FastAPI, `TestClient`, Pydantic / `evidence_gate`, `practice_query` | 미지원 질문 → `{"status":"insufficient_evidence","answer":None,"citations":[]}` |

### 7.0.2 Week 2 — 같은 라이브러리의 다른 사용법

| 파일 | 역할 | 사용 라이브러리 / 정의 심볼 | 고정하는 계약 |
|---|---|---|---|
| `01_structured_ticket_classification` | 자유 텍스트 → 제한된 판단값 | `Literal`, Pydantic / `TicketClassification` | schema 밖 값을 fallback category로 바꾸지 않고 validation 실패로 드러냄 |
| `02_metadata_filtered_retrieval` | 검색 범위 통제. 분류 결과를 filter로 사용 | `Document` / `metadata_filter`, `practice_retrieve_playbook` | 유사도 계산 **이전에** filter 적용. 해당 category가 없으면 다른 category를 빌리지 않고 `[]` |
| `03_conditional_resolution_routing` | 분기 문법. Week 1 선형 그래프와 대비 | `StateGraph` + **`add_conditional_edges`** / `choose_route`, `billing_queue`, `incident_escalation` | billing queue와 incident escalation이 실제로 다른 node를 지나감 |
| `04_ticket_workflow_evaluation` | **2주차 통합 + 평가표**. `classify → filtered retrieval → evidence gate → route` 축소 pipeline | **import 0개(순수 Python)** / `classify_ticket`, `retrieve_playbook`, `evidence_gate`, `practice_ticket_pipeline` | table-driven으로 category·route·status·citation 일관성. 근거 없으면 `needs_more_information` |

### 7.0.3 Week 3 — 멀티에이전트 안전 제어

| 파일 | 역할 | 사용 라이브러리 / 정의 심볼 | 고정하는 계약 |
|---|---|---|---|
| `01_multi_agent_state_ownership` | **멀티에이전트 = 역할 이름이 아니라 state write 책임 분리** | `TypedDict` / `IncidentState`, `triage/investigator/commander_node`, `apply_owned_update` | 역할 밖 필드 write는 실행 중 거부(`cannot write`). `executed_commands == []` |
| `02_bounded_revision_loop` | 되돌아가는 edge와 종료 보장. Week 2의 1회 분기와 대비 | `StateGraph` + 조건부 loop / `review_node`, `revise_node`, `fail_closed`, `choose_review_path` | 한도 소진 시 성공으로 위장하지 않고 `fail_closed`. `revision_count == max_revisions` |
| `03_command_safety_human_approval` | **모델이 붙인 flag를 믿지 않는 결정론적 검사** | Pydantic / `CommandProposal`, `proposal_is_safe`, `build_approval_packet` | `dry_run=True`여도 명령 문자열 자체를 검사. SEV1/2 → 승인 packet, SEV3 → observation plan, 항상 `executed_commands == []` (assert 11개) |
| `04_incident_workflow_failure_tests` | **실패 행렬 회귀 평가** | **import 0개(순수 Python)** / `practice_validate_severity`, `practice_incident_guard` | 빈 proposal·혼합 proposal·한도 소진·잘못된 severity 어디서도 명령이 실행되지 않음 (assert 11개) |

### 7.0.4 두 가지 설계 의도 — 복제 시 반드시 가져갈 것

1. **마지막 노트북은 import 0개의 순수 Python으로 쓴다.** `week2/04`, `week3/04`가 그렇다. 라이브러리 사용법이 아니라 *계약*을 가르치는 자리이기 때문이다. `week3/04`가 직접 명시한다 — "이 계약은 역할 node나 loop 구현이 바뀌어도 유지돼야 합니다."
2. **마지막 주차의 안전 노트북은 테스트 대상 코드이기도 하다.** `tests/test_curriculum_contract.py`가 `week3/03`·`week3/04`의 코드 셀을 `exec`한 뒤 그 안의 `CommandProposal`·`proposal_is_safe`·`build_approval_packet`·`practice_incident_guard`를 **직접 호출**해 공격 문자열 6종(개행, 리다이렉트 `>`, `&`, `$VAR`, 백틱, 백슬래시)과 혼합 proposal, SEV 분기를 검증한다. 교재와 명세가 같은 파일이다.

### 7.0.5 같은 문법의 재등장 — 허용 조건과 필수 조건

노트북 제공 여부를 가르는 기준은 **라이브러리·문법이 아니라 기법(사용 패턴)** 이다. 같은 문법이라도 다른 주차에서 다른 기법으로 쓰인다면 실습 예제로 다시 제공한다. 루트 README의 원문이 이 규칙이다 — *"같은 라이브러리도 활용 방식이 다르면 새로운 실습으로 다룹니다."*

**단, 재등장에는 조건이 붙는다. 그 기법에 맞는 다른 시나리오를 반드시 함께 제공해야 한다.** 문법만 다르게 쓰고 앞 주차의 상황을 재활용하면, 학습자에게는 같은 실습의 변형으로 보여 새 기법이 왜 필요한지가 드러나지 않는다. 기법이 바뀌면 그 기법이 아니면 풀 수 없는 상황을 새로 가져와야 한다.

#### 판정 규칙

| 겹치는 것 | 판정 | 이유 |
|---|---|---|
| 라이브러리·문법만 겹침 | **제공한다** | 같은 도구의 다른 사용법은 별개의 학습 내용 |
| 기법(사용 패턴)이 겹침 | 제공하지 않는다 | 이전 주차에서 이미 배운 것 |
| 기법은 새로운데 시나리오가 겹침 | **제공하되 시나리오를 새로 만든다** | 새 기법의 필요성이 드러나지 않음 |

#### 저장소 실증 — 재등장 2건 모두 시나리오가 다르다

`StateGraph` (3회 재등장)

| 주차 | 기법 | 시나리오 |
|---|---|---|
| W1-04 | `add_edge`만 — 선형 | 정책 질문이 `retrieve → answer`를 순서대로 지나가게 한다 |
| W2-03 | `add_conditional_edges` — 1회 분기 | 일반 billing 문의는 billing queue로, urgent 장애는 incident escalation으로 경로를 나눈다 |
| W3-02 | 이전 node로 돌아가는 bounded loop | 위험한 proposal을 commander로 되돌려 수정하되 `max_revisions` 소진 시 `fail_closed`로 닫는다 |

`Pydantic BaseModel` (4회 재등장)

| 주차 | 기법 | 시나리오 |
|---|---|---|
| W1-01 | `Field` 제약으로 입력 검증 | 빈 질문·너무 짧은 질문을 검색 전에 거부한다 |
| W1-05 | request/response 모델 + endpoint | 지원·미지원 질문을 `TestClient`로 비교한다 |
| W2-01 | `Literal` structured output schema | 자유 형식 문의를 category·priority·reason으로 변환하고 잘못된 출력은 거부한다 |
| W3-03 | 명령 제안 구조화 | 모델이 제안한 명령을 allowlist와 shell 제어 문자 검사로 걸러 승인 packet과 observation plan으로 나눈다 |

각 행의 시나리오는 그 기법이 아니면 풀리지 않는다. 선형 graph로는 W2의 2경로 분기를 표현할 수 없고, 1회 분기로는 W3의 재검토 상한을 표현할 수 없다. **시나리오가 기법의 존재 이유를 증명하는 구조**다.

전체 13개 노트북의 `시나리오` 문장은 모두 서로 다르다 (13/13 고유).

#### 복제 시 체크리스트

새 주차에 노트북을 추가할지 판단할 때 순서대로 묻는다.

1. 이 **기법**이 이전 주차 노트북에 이미 나왔는가? → 나왔으면 만들지 않는다. (라이브러리가 같은 것은 이유가 되지 않는다)
2. 새 기법이라면, 이 기법이 **아니면 풀 수 없는 상황**을 시나리오로 잡았는가? → 앞 주차 시나리오의 변형이면 다시 잡는다.
3. 그 시나리오가 해당 주차 app의 도메인 안에 있는가? → `실제 app 연결` 절에서 app의 어느 흐름으로 확장되는지 이을 수 있어야 한다.
4. 계약 테스트에 **양성·음성 assert**를 함께 넣었는가? (아래)

#### 계약 테스트로 강제하는 법

기법 중복은 "이번 주차에 무엇이 있어야 한다"(양성)와 **"이전 주차에 무엇이 없어야 한다"(음성)** 를 쌍으로 걸어 막는다. 저장소의 실제 코드:

```python
self.assertIn(".add_edge(", week1)
self.assertNotIn(".add_conditional_edges(", week1)   # W1은 분기를 쓰면 안 된다
self.assertIn(".add_conditional_edges(", week2)
self.assertIn("choose_route", week2)
self.assertIn(".add_conditional_edges(", week3)
self.assertIn("revision_count", week3)
self.assertIn("max_revisions", week3)
```

"반복하지 마라"가 아니라 **"반복하지 않았음을 증명하라"** 이다.

다만 현재 계약 테스트는 시나리오 중복을 검사하지 않는다 (`시나리오` 헤딩의 존재만 확인). 새 프로젝트에서는 다음 검사를 추가할 것을 권장한다.

```python
def test_every_notebook_has_a_distinct_scenario(self):
    scenarios = {}
    for relative_path in REQUIRED_CODE_TERMS:
        prose = self.notebook_parts(relative_path)[0]
        body = re.search(r"## 시나리오\n(.*?)(?=\n##)", prose, re.S)
        self.assertIsNotNone(body, relative_path)
        scenarios[relative_path] = " ".join(body.group(1).split())
    self.assertEqual(len(set(scenarios.values())), len(scenarios), scenarios)
```

### 7.0.6 노트북에서 실습한 기법은 app.py에 도달해야 한다

노트북은 연습이고 `app.py`는 **실제로 동작해야 하는 코드**다. 그 주차 노트북이 가르친 기법이 해당 주차 `app.py`에 쓰이지 않으면 커리큘럼은 이미 깨진 것이다. 실습 시나리오와 app의 시나리오는 달라도 되지만(노트북은 이해를 위한 축소판), **기법은 같아야 한다.**

`app.py`가 "실제로 동작한다"는 말의 조건은 세 가지다.

1. 사용자가 쓸 수 있는 UI가 있다 — 단 UI는 `app.py`가 아니라 Streamlit 계층이 제공하고, `app.py`는 그 UI가 호출하는 HTTP API와 `/docs`를 낸다.
2. 실제 문서로 만든 DB를 검색한다 — `knowledge/*.md` → `shared/ingest.py` → pgvector. 단 이것은 `APP_MODE=live`에서만이고, 기본 `fixture`는 파일 안의 축소 corpus를 쓴다.
3. 실제 LLM API를 호출해 결과를 본다 — `generate_grounded_text`, `generate_structured`. 역시 live 한정이며, 응답의 `mode` 키가 둘을 구분한다.

#### 강제 방법

`tests/test_curriculum_contract.py`의 `APP_TECHNIQUE_COVERAGE`가 **기법 → (노트북 경로, app에서 확인할 코드 용어)** 를 매핑하고, 각 `app.py` 원문에 그 용어가 남아 있는지 검사한다. 노트북 경로를 함께 들고 있어 실패 메시지가 구현을 잃은 수업을 지목한다.

```
AssertionError: week2/app.py no longer uses 'metadata filter'
                from week2/notebooks/02_metadata_filtered_retrieval.ipynb
```

짝이 되는 음성 검사도 둔다 — `test_week1_app_stays_linear_so_week2_can_introduce_branching`은 Week 1 app에 `add_conditional_edges`가 **없어야** 한다고 단언한다. 난이도 순서가 app 쪽에서도 유지된다.

#### 이 규칙이 왜 필요한지 — 실제로 깨졌던 사례

이 저장소의 `bcdc7f5` 커밋("feat: add live RAG policy lab")은 live RAG를 붙이면서 Week 2·3 앱을 통째로 교체했고, 그 과정에서 `TicketClassification`(structured output), `filter={"category": ...}`(metadata filter), `CommandProposal`·allowlist·`max_revisions`·`executed_commands`(command safety)가 모두 사라졌다. 노트북과 README는 교체 전 앱을 계속 설명했고, 주차별 테스트 3개는 ImportError로 죽은 채 방치됐다. 위 계약 테스트가 있었다면 그 커밋에서 즉시 실패했을 것이다.

### 7.1 계약 검사 — `tests/test_curriculum_contract.py`

노트북을 **문서가 아니라 계약**으로 취급한다.

### 7.2 구조 규칙
- 주차별 노트북 **파일명 집합이 테스트에 하드코딩**되어 있다. 파일을 더하거나 빼면 실패한다.
- markdown 셀 ≥ 3, code 셀 ≥ 3.
- markdown 전체에 다음 헤딩이 **모두** 있어야 한다: `시나리오`, `학습 목표`, `직접 조립`, `중간 결과`, `실제 app 연결`, `실패 경계`, 그리고 `다음 Notebook 연결`.
- code 셀마다 주석 ≥ 2개, 모든 `def`/`class` 바로 위 2줄 안에 주석이 있어야 한다.
- 전체 주석의 **고유 비율 ≥ 70%** — 복붙한 상투 주석을 막는다. 특정 금지 문구는 문자열로 직접 차단.

### 7.3 "완성 코드를 부르지 말 것" 이중 차단
```python
FORBIDDEN = {"from week1.app", "import week1.app", "run_policy_query",
             "create_app", "build_workflow", ...}
```
문자열 검사 + **AST 검사**(import 이름, 호출 이름) 두 겹으로 막는다. 노트북은 app 함수를 호출하지 않고 primitive를 **직접 조립**해야 한다.

### 7.4 "무엇을 가르쳤는지"까지 검사
노트북 경로별 **필수 코드 용어 화이트리스트**가 있다.
```python
"week1/.../02_documents_and_splitting.ipynb": {"Document(", "RecursiveCharacterTextSplitter", ".split_documents("}
"week3/.../02_bounded_revision_loop.ipynb":   {"StateGraph(", "revision_count", "max_revisions", ".add_conditional_edges(", "fail_closed"}
```
추가로 **같은 라이브러리의 서로 다른 사용법**을 교차 검증한다 — W1 노트북은 `add_conditional_edges`를 쓰면 안 되고, W2는 반드시 써야 하며, W3는 `revision_count`/`max_revisions`가 있어야 한다.

### 7.5 실행 의미 검증
테스트가 노트북 코드 셀을 `exec`해서 네임스페이스를 꺼낸 뒤, 그 안의 함수를 실제로 호출해 안전 규칙을 확인한다.
- 개행·리다이렉트·`&`·`$VAR`·백틱·백슬래시가 섞인 명령은 `dry_run=True`여도 전부 차단되는가
- 안전+위험 명령이 섞이면 전체가 `blocked_manual_review`가 되고 `proposed_commands == []`가 되는가
- 모든 경로에서 `executed_commands == []`인가
- 노트북의 fallback/severity 의미가 app의 의미와 일치하는가

### 7.6 로컬 기본값 고정
README와 compose 파일에서 "fixture 기본 + loopback 전용" 문자열의 존재를 직접 assert 한다.

### 7.7 코드 셀 작성 패턴
모든 code 셀은 다음 2줄 주석으로 시작한다.
```python
# 실행 순서: N단계 · <제목>에서 <대상>을(를) 먼저 구성합니다.
# 관찰 포인트: 이 셀의 출력이 다음 단계에서 사용할 입력 계약을 충족하는지 확인합니다 — N단계 · <제목>.
```
fixture 식별자는 `practice_` / `mini_` / `sample_` 접두 또는 `evaluation_cases` / `failure_cases`. 셀 마지막에는 `assert`로 눈으로 본 결과를 계약으로 고정한다.

---

## 8. 문서 세트 규격

| 파일 | 역할 | 필수 절 |
|---|---|---|
| `README.md` | 전체 입구 | 주차별 누적 구조 표, **개념 진행표**, Python 설치, Docker→pgvector 기동, live 실행, Windows PowerShell 별도 절, 구현 경계 |
| `week<N>/README.md` | 주차 교안 | 프로젝트 결과 + ASCII 흐름도 / 선행 조건(반복 안 함) / 이번 주 새로 배우는 것 / 아직 다루지 않는 것 / 핵심 코드 / 노트북 순서 / 실행·완료 기준 / 다음 주 연결 |
| `docs/runtime-flow-for-beginners.md` | 초심자용 | ASCII 전체 흐름도, **등장인물 표**(Docker=도시락통, pgvector=문서 상자 식 비유), 중요한 약속, 실행 순서 5단계 |
| `docs/week<N>-running-files.md` | 주차 실행 안내 | 한 줄 목표 / 최소 실행 명령 4개 / 실제로 움직이는 파일 / 질문 한 번의 여행 |
| `docs/<인프라>-setup.md` | 환경 구축 | 설치 확인부터 정상 동작 기준·중지/초기화·자주 발생하는 문제까지 12절 |
| `knowledge/README.md` | 데이터 고지 | 가상 문서임을 명시 |

문서 규칙: 모든 완료 기준은 **관찰 가능한 문장**으로 쓴다("미지원 질문은 답변을 만들지 않는다"). 명령은 복붙 가능한 코드블록으로, 주석은 한국어로 단다.

---

## 9. 테스트 배치

| 위치 | 대상 |
|---|---|
| `tests/test_curriculum_contract.py` | 커리큘럼·노트북 계약(§7) + **app↔노트북 기법 연결**(§7.0.6) + 시나리오 고유성(§7.0.5) |
| `tests/test_live_rag.py` | fixture 기본값, live 설정 검증, live 경로가 검색된 문서로만 생성하는지 (네트워크 mock) |
| `tests/test_ingest.py` | 주차별 Markdown 원본 존재와 메타데이터 안정성 |
| `tests/test_streamlit_app.py` | `AppTest` + `ui_common.call_workflow_api` 패치로 UI를 실제 렌더링하고 3주차 시나리오 클릭 |
| `week<N>/tests/test_*.py` | 주차별 워크플로 성공/실패 계약, `TestClient` 통합 |

원칙: **외부 의존 없이 전 테스트가 돈다.** OpenAI·DB는 mock 또는 fixture 모드. 실행 명령은 `python -m unittest discover -s . -p 'test_*.py' -v`.

---

## 10. 다른 주제로 복제하는 절차

### 10.1 그대로 두는 것 (구조 = 자산)
`shared/live_rag.py`의 전체 함수 시그니처, `ui_common.py`의 렌더링·진단 골격, `tests/test_curriculum_contract.py`의 검사 종류, 응답 공통 키, status 어휘 분류, 오류 계약, 문서 파일 구성, 포트 규약, 4계층 경계.

### 10.2 치환 표
| 치환 대상 | 현재 값 | 새 프로젝트에서 정할 것 |
|---|---|---|
| 가상 조직 | NoriWorks (B2B SaaS) | 새 도메인의 가상 주체 |
| 주차 시나리오 | 휴가 / 출장비 / IT 변경 | 난이도 1·2·3에 대응하는 업무 3개 |
| `business_use_case` | `hr_leave_policy_self_service` 등 | snake_case 식별자 3개 |
| 벡터 테이블 | `agent_workflow_week1..3` | `<prefix>_week1..3` |
| POST 경로 | `/query`, `/review`, `/review-change` | 도메인 동사 3개 |
| 입력 스키마 | `question` / `amount+receipt_attached+purpose` / `request+user_role` | 주차별 Pydantic 필드 |
| 결정론 규칙 | 영수증 누락 → `receipt_required` | LLM에 맡기면 안 되는 규칙 1개 이상 |
| 위험 탐지 | "무시·우회·예외·긴급 배포" 키워드 | 도메인의 정책 우회 신호 |
| W3 안전 대상 | kubectl 명령 allowlist | 도메인의 위험 행위 allowlist |
| 노트북 파일명·필수 용어 | 5+4+4개 | 새 주제에 맞춰 **테스트와 함께** 재정의. 재등장 문법은 기법+시나리오를 쌍으로 새로 정의 (§7.0.5) |
| 라벨 사전 | `NODE_LABELS`, `STATUS_LABELS`, `USE_CASE_LABELS` | 새 node·status 한국어 라벨 |

### 10.3 권장 작업 순서
1. 3주 커리큘럼 설계 먼저 — 무엇을 어느 주차에 **처음** 가르치고 어디서 재사용할지 개념 진행표를 짠다. 같은 문법이 여러 주차에 걸친다면 주차별 **기법**과 **그 기법 전용 시나리오**를 이 단계에서 함께 정한다 (§7.0.5).
2. `knowledge/` 정책 문서를 쓴다. 답변 가능 범위가 곧 시스템의 능력 범위다.
3. 주차별 `app.py`를 4.2 응답 계약에 맞춰 만든다 (fixture 경로 먼저, live 경로 나중).
4. `tests/test_curriculum_contract.py`의 파일명 집합·필수 용어를 **먼저** 새 주제로 고친다.
5. 노트북을 계약에 맞춰 작성한다. 테스트가 곧 체크리스트다.
6. Streamlit 페이지와 라벨 사전을 채운다.
7. 문서 세트(8장) 6종을 쓴다.
8. 전 테스트를 fixture 모드로 통과시킨 뒤에만 live 환경을 붙인다.

---

## 11. 저장소 상태 — 고친 것과 남은 것

### 11.1 이 청사진 작성 중 복원한 것

`bcdc7f5`에서 탈락했던 커리큘럼 기법을 **현재 도메인(출장비 검토 / IT 변경 검토)에 이식**해 되살렸다. 전체 48개 테스트가 통과한다.

| 항목 | 내용 |
|---|---|
| `shared/live_rag.py` | `retrieve_documents(_with_trace)`에 `metadata_filter` 인자 추가. 구조화 판단용 `generate_structured()` 추가 |
| `shared/ingest.py` | Markdown `카테고리:` 헤더를 읽어 `category` 메타데이터 부여 |
| `knowledge/week2/` | transport·lodging·meal 카테고리 playbook 3종 추가, 기존 2종에 `카테고리: other` 부여 |
| `week2/app.py` | `ExpenseClassification`(`Literal`) structured output + 분류 category로 필터링한 검색 + `manager_review` 분기 추가 |
| `week3/app.py` | `CommandProposal`, `OBSERVATION_ALLOWLIST`, shell 제어 문자 차단, `proposal_is_safe()`, `MAX_REVISIONS` bounded loop, SEV1/2 `approval_packet` · SEV3 `observation_plan`, 누적 `rejected_history`, 항상 `executed_commands: []` |
| `week1/app.py`, `week2/app.py` | import되지 않은 `retrieve_documents`를 부르던 죽은 live 분기 제거 (구 §11-1 버그) |
| `ui_common.py`, `app_pages/week3.py` | 새 status·분류·명령 packet 렌더링, SEV 등급 입력 |
| 테스트 | 죽어 있던 `test_policy_qa`·`test_ticket_workflow`·`test_incident_command`와 낡은 `tests/test_notebooks.py` 제거, `week2/tests/test_expense_workflow.py`·`week3/tests/test_change_review.py` 신규 작성(구 스위트의 안전 단언 전부 이관) |
| 계약 테스트 | `test_each_app_uses_the_techniques_its_week_practised`, `test_week1_app_stays_linear_...`, `test_every_notebook_has_a_distinct_scenario`, JSON 리터럴 검사 이관 |
| 문서 | 루트 README의 삭제된 노트북 목록 교체, 주차 README 3종의 없는 심볼·삭제된 테스트 경로 정정 |

### 11.2 남아 있는 문제 — 새 프로젝트에 복제하지 말 것

1. **RAG 구현이 두 벌** — `lab_core.py`(`PGVector`, `LiveSettings`, `OPENAI_CHAT_MODEL`)와 `shared/live_rag.py`(`PGVectorStore`, `LiveRagSettings`, `OPENAI_MODEL`)가 공존하고 앱은 후자만 쓴다. `lab_core`는 `tests/test_live_retrieval_contract.py`만 참조한다. 새 프로젝트는 **한 벌로 통일**할 것.
2. **Compose 파일 두 벌이 불일치** — `infra/compose.pgvector.yml`(5432, `app_user`/`agent_workflow`, 문서가 쓰는 쪽) vs `docker-compose.yml`(6024, `langchain`/`langchain`). 루트 README 2-2절은 6024 연결 문자열을, `.env.example`과 `docs/docker-pgvector-live-rag-setup.md`는 5432를 안내한다.
3. **Dockerfile이 앱을 담지 못한다** — `lab_core.py`와 `week1..3`만 COPY하므로 `shared/`·`knowledge/`·`app_pages/`가 없어 컨테이너로는 기동되지 않는다. README도 "Compose runtime은 검증하지 않았다"고 명시한다.
4. **UI 경계가 완전하지 않다** — `app_pages/week2.py`, `app_pages/week3.py`가 `from week2.app import ExpenseRequest`처럼 서버 모듈의 Pydantic 모델을 직접 import한다. 워크플로 실행은 HTTP지만 프로세스가 완전히 분리되지는 않아, Streamlit만 별도 호스트에 배포할 수 없다. `app_pages/week1.py`는 인라인 검증으로 이 문제가 없다.
5. **주차 README의 도메인 서술이 부분적으로만 갱신됐다** — 핵심 코드·실행 명령·완료 기준은 현재 구현에 맞췄지만, 본문 설명 일부는 여전히 교체 전 어휘를 남기고 있을 수 있다.
6. **잔재 파일** — 비어 있는 `labs/__init__.py`.
7. **live 모드는 DB까지만 검증했고 OpenAI 호출은 미검증이다** — 아래 §11.3 참조.

### 11.3 live 검증 결과

실제 PostgreSQL 16 + pgvector 0.8.6 컨테이너(`infra/compose.pgvector.yml`, 127.0.0.1:5432)에 대해 확인했다. OpenAI 호출부만 결정적 스텁으로 대체하고, 설정 파싱·테이블 생성·적재·필터 검색·trace 구성·임계값·citation 조립은 전부 실제 코드가 실제 DB에 대해 실행됐다.

| 확인 항목 | 결과 |
|---|---|
| `filter={"category": ...}`가 기본 `langchain_metadata` JSONB에서 동작하는가 | **동작한다.** 선언된 `metadata_columns` 방식과 JSONB 기본 방식 모두 정확히 해당 category만 반환 |
| `vector` extension | `PGEngine.init_vectorstore_table`이 자동 생성한다. compose가 만들지 않아도 됨 (설치 문서 6절의 수동 `CREATE EXTENSION`은 중복 안전장치) |
| 실제 `knowledge/week2` 적재 | 5개 파일 → 6 chunk. `category` 메타데이터가 DB까지 보존됨 |
| 주차별 category 격리 | lodging·transport·meal 각각 자기 playbook만 인용. 교차 오염 없음 |
| Week 1·3 live 경로 | 실제 DB 검색 → citation·retrieval_trace 정상. W3는 재검토 1회 후 `human_approval_required`, `executed_commands=[]`, 차단 이력 보존 |
| 관련도 임계값 게이트 | `RAG_MIN_RELEVANCE=0.999`에서 후보 3건 전부 `selected=False` → `insufficient_evidence`, `answer=None`, `citations=[]` |
| `collection_diagnostics` | 실제 chunk 수 반환, API 키는 앞 5자만 노출 |
| 벡터 id 형식 | `PGVectorStore`는 id 컬럼이 uuid다. `ingest_documents`의 `uuid5` 생성이 이 제약을 이미 충족한다 (임의 문자열 id는 `DataError`) |

**아직 검증되지 않은 것 — 실제 OpenAI 키가 필요하다**

- `OpenAIEmbeddings`가 `OPENAI_EMBEDDING_DIMENSIONS=1536`으로 테이블·질의 양쪽에서 일관되게 동작하는지
- `generate_structured()`의 `with_structured_output(ExpenseClassification)` 반환값이 `model_validate` 경로를 통과하는지 (dict와 모델 인스턴스 양쪽 분기)
- `generate_grounded_text()`가 근거 밖 내용을 만들지 않는지, 근거 부족 시 "근거가 부족합니다"를 반환하는지
- 실제 임베딩 유사도에 대해 기본값 `RAG_MIN_RELEVANCE=0.25`가 적절한 경계인지 (스텁 벡터로는 판단 불가)

새 프로젝트에서는 (a) RAG 구현 1벌, (b) compose 1벌 + 실제로 동작하는 Dockerfile, (c) UI는 HTTP만, (d) **문서·테스트·코드 중 하나를 바꾸면 나머지 둘을 같은 커밋에서 고친다** 는 규율을 처음부터 지킬 것. (d)를 사람의 규율에 맡기지 말고 §7.0.6의 계약 테스트로 강제하는 것이 이 저장소가 준 가장 큰 교훈이다.
