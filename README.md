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

# 주차별 API 서버 예시
.venv/bin/uvicorn week1.app:app --port 8011
.venv/bin/uvicorn week2.app:app --port 8012
.venv/bin/uvicorn week3.app:app --port 8013

# Notebook UI 실행
.venv/bin/jupyter notebook
```

`pip` 환경이라면 `python -m pip install -r requirements.txt`를 사용합니다.

## Notebook 순서

1. `01_fastapi.ipynb`
2. `02_langchain_rag.ipynb`
3. `03_langgraph_workflow.ipynb`
4. `04_agent_evaluation.ipynb`
5. `05_deployment_testing.ipynb`

## 구현 경계

- LangChain `Document`, text splitter, Runnable과 LangGraph `StateGraph`를 실제 코드에서 사용합니다.
- local fixture와 결정론적 retrieval을 사용하므로 API key 없이 재현됩니다.
- live LLM, 외부 embedding/vector store, 실제 업무 문서, write-capable Tool은 포함하지 않습니다.
- `.env`, API key, 개인정보는 커밋하지 않습니다.
- Compose artifact는 제공하지만 현재 환경에서 Compose runtime은 검증하지 않았습니다.
