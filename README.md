# LangChain RAG + LangGraph 현업 워크플로우 Weekly Labs

매주 독립 프로젝트 하나를 완성 코드부터 실행한 뒤, 같은 주 폴더의 Notebook으로 LangChain RAG·LangGraph 멀티에이전트·FastAPI·검증·배포 artifact를 분해해 실습하는 저장소입니다.

## 학습 경로

```text
week1/  # 1/5 — HR 휴가 규정 셀프서비스 보조
week2/  # 2/5 — 재무 출장비 정산 사전 검토
week3/  # 3/5 — IT 변경 요청 위험 검토·승인 준비
```

각 폴더는 `app.py · tests/ · notebooks/ · deploy/ · README.md`를 포함합니다. README에는 사용자·입력·산출·실패 비용·자동화 금지 경계를 함께 기록합니다.

## 한 번에 설치·실행

Week 1~3의 FastAPI·LangChain·LangGraph·테스트·Notebook 실행 의존성은 root `requirements.txt` 하나로 설치합니다.

```bash
# repository root에서 실행
uv venv
uv pip install -r requirements.txt

# 전체 자동 테스트
.venv/bin/python -m unittest discover -s . -p 'test_*.py' -v

# 주차별 FastAPI 서버 예시 (한 번에 하나만 실행)
.venv/bin/uvicorn week1.app:app --port 8011
.venv/bin/uvicorn week2.app:app --port 8012
.venv/bin/uvicorn week3.app:app --port 8013

# Week 1~3 통합 Streamlit UI
.venv/bin/streamlit run streamlit_app.py

# Notebook UI 실행
.venv/bin/jupyter notebook
```

`pip` 환경이라면 `python -m pip install -r requirements.txt`를 사용합니다.

### Windows PowerShell 실행

저장소 루트(`agent-workflow-lab`)에서 아래 명령을 실행합니다.

```powershell
# 의존성 설치 (최초 한 번)
uv venv
uv pip install -r requirements.txt

# 전체 자동 테스트
.\.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py" -v

# FastAPI 서버: 필요한 주차 하나만 실행하고 Ctrl+C로 종료
.\.venv\Scripts\uvicorn.exe week1.app:app --port 8011
.\.venv\Scripts\uvicorn.exe week2.app:app --port 8012
.\.venv\Scripts\uvicorn.exe week3.app:app --port 8013

# Week 1~3 통합 Streamlit UI: 필요한 FastAPI 서버를 먼저 실행
.\.venv\Scripts\streamlit.exe run streamlit_app.py
```

FastAPI 서버는 각 주소의 `/docs`에서 대화형 API 문서를 제공합니다.

- Week 1: `http://127.0.0.1:8011/docs` (`POST /query`)
- Week 2: `http://127.0.0.1:8012/docs` (`POST /review`)
- Week 3: `http://127.0.0.1:8013/docs` (`POST /review-change`)

Streamlit은 실행 후 표시되는 로컬 주소(기본 `http://localhost:8501`)를 브라우저에서 엽니다. 상단 메뉴에서 Week 1~3을 전환하고 폼을 제출하면, 해당 주차 FastAPI의 HTTP API로부터 workflow 결과·근거·실행 trace를 받습니다. 기본 주소는 `127.0.0.1:8011`~`8013`이며, 배포 환경에서는 `WEEK1_API_URL`, `WEEK2_API_URL`, `WEEK3_API_URL`로 각각 바꿀 수 있습니다.

## Notebook 순서

1. `01_fastapi.ipynb`
2. `02_langchain_rag.ipynb`
3. `03_langgraph_workflow.ipynb`
4. `04_agent_evaluation.ipynb`
5. `05_deployment_testing.ipynb`

## 구현 경계

- LangChain `Document`, text splitter, Runnable과 LangGraph `StateGraph`를 실제 코드에서 사용합니다.
- 기본 `APP_MODE=fixture`는 local fixture와 결정론적 retrieval을 사용하므로 API key 없이 재현됩니다.
- `APP_MODE=live`는 OpenAI 임베딩·채팅 모델과 PostgreSQL/pgvector 검색을 사용합니다. [Live RAG 설정 안내](docs/docker-pgvector-live-rag-setup.md)를 따라 DB를 시작하고 문서를 적재해야 합니다.
- live 모드는 근거 문서가 없을 때 모델 호출이나 승인 대신 `insufficient_evidence`로 안전하게 종료합니다. 실제 업무 변경을 수행하는 Tool은 포함하지 않습니다.
- `.env`, API key, 개인정보는 커밋하지 않습니다.
- Compose artifact는 제공하지만 현재 환경에서 Compose runtime은 검증하지 않았습니다.
