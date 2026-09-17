# LangChain RAG + LangGraph 현업 Workflow 3주 실습

완성된 애플리케이션을 먼저 실행한 뒤, 주차별 Notebook에서는 app 함수를 호출하지 않고 app에 쓰인 라이브러리 primitive와 필수 pipeline을 작은 현업 시나리오로 직접 조립합니다. 같은 라이브러리도 활용 방식이 다르면 새로운 실습으로 다룹니다. 모든 업무 자료는 합성 fixture이며 실제 휴가 승인, 환불, 계정 변경, 운영 명령을 실행하지 않습니다.

## 주차별 누적 구조

| 주차 | 난이도 | 프로젝트 | 이번 주에 처음 배우는 핵심 |
|---|---:|---|---|
| [Week 1](week1/README.md) | 1/5 | HR 규정 Q&A | Pydantic/FastAPI 경계, `Document`, splitter, retrieval, citation, 선형 `StateGraph`, 통합 테스트 |
| [Week 2](week2/README.md) | 2/5 | 고객지원 티켓 분류·해결 계획 | structured output, metadata filter, 조건부 edge, 다중 경로 평가 |
| [Week 3](week3/README.md) | 3/5 | 운영 장애 대응 멀티에이전트 지휘 시스템 | 역할별 state 소유권, 제한 재검토 loop, 명령 allowlist, 사람 승인, fail-closed |

### 개념 진행표

| 개념 | Week 1 | Week 2 | Week 3 |
|---|---|---|---|
| FastAPI/Pydantic·기본 RAG·citation | **도입·실습** | 재사용(재설명하지 않음) | 재사용 |
| structured output·metadata filter·conditional routing | 범위 밖 | **도입·실습** | 선행 조건으로 재사용 |
| 역할 분리·bounded loop·HITL·command safety | 범위 밖 | 범위 밖 | **도입·실습** |
| 실제 write/운영 명령 실행 | 금지 | 금지 | 금지 |

`fixture` 모드는 API key와 DB 없이 결정적으로 실행됩니다. `live` 모드는 `ChatOpenAI`, `OpenAIEmbeddings`, PostgreSQL+pgvector(`langchain-postgres`)를 실제 사용합니다. 모든 API 응답은 `mode`를 표시하므로 fixture 결과를 live 실행 증거로 오인하지 않습니다.

## 1. Python 환경 설치

저장소 루트에서 실행합니다.

```bash
uv venv --python 3.13
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m unittest discover -s . -p 'test_*.py' -v
```

API key 없이 실행:

```bash
APP_MODE=fixture .venv/bin/uvicorn week1.app:app --port 8011
APP_MODE=fixture .venv/bin/uvicorn week2.app:app --port 8012
APP_MODE=fixture .venv/bin/uvicorn week3.app:app --port 8013
```

`APP_MODE`는 `fixture` 또는 `live`만 허용합니다. 오타는 fixture로 조용히 대체하지 않고 시작 단계에서 실패합니다.

## 2. Docker 설치 확인부터 pgvector 기동까지

### 2-1. Docker 설치

Docker Desktop(Windows/macOS) 또는 Docker Engine+Compose v2(Linux)를 설치한 뒤 아래 두 명령이 모두 성공해야 합니다.

```bash
docker --version
docker compose version
```

두 번째 명령이 `docker: 'compose' is not a docker command`로 실패하면 Compose v2 plugin을 추가 설치한 뒤 다시 확인합니다. 이 저장소는 구형 `docker-compose` 명령이 아니라 `docker compose`를 기준으로 합니다.

### 2-2. 환경 파일 준비

```bash
cp .env.example .env
```

`.env`에서 `OPENAI_API_KEY`를 채웁니다. 실제 key·운영 DB 정보는 commit하지 않습니다. 로컬 기본 연결 문자열은 다음 형식입니다.

```text
postgresql+psycopg://langchain:langchain@localhost:6024/langchain
```

`langchain-postgres`는 psycopg3를 사용하므로 driver 이름은 `postgresql+psycopg`입니다.

### 2-3. Compose 검증·DB 시작

```bash
docker compose config
docker compose up -d pgvector
docker compose ps
```

`pgvector`가 `healthy`가 될 때까지 확인한 뒤 extension을 검증합니다.

```bash
docker compose exec pgvector \
  psql -U langchain -d langchain -c '\dx vector'
```

`vector` 행이 표시되면 `docker/postgres/init.sql`의 `CREATE EXTENSION IF NOT EXISTS vector`가 적용된 것입니다. 첫 기동에서 **PostgreSQL/extension 초기화**가 이루어지고, 애플리케이션 live 시작 시 **LangChain collection table 생성과 학습 corpus embedding/seeding**이 별도로 수행됩니다.

Compose는 교육 환경의 PostgreSQL major version을 고정하기 위해 `pgvector/pgvector:pg16` tag를 사용합니다. 이 tag는 digest까지 고정한 완전 재현 pin은 아니므로 장기 운영에서는 검증한 image digest로 고정해야 합니다.

### 2-4. live 모드 실행

```bash
set -a
. ./.env
set +a
APP_MODE=live .venv/bin/uvicorn week1.app:app --port 8011
```

Week 2·3은 각각 `week2.app:app --port 8012`, `week3.app:app --port 8013`으로 실행합니다. 세 주차는 같은 DB에서 서로 다른 collection을 사용합니다.

세 API 컨테이너까지 한 번에 빌드·기동하려면 `.env`에 key를 넣은 뒤 `apps` profile을 사용합니다.

```bash
docker compose --profile apps up -d --build
docker compose --profile apps ps
```

기본 `docker compose up -d pgvector`는 DB만 시작하므로 OpenAI 비용이 발생하지 않습니다.

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
