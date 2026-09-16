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
curl -s http://127.0.0.1:8011/health
curl -s -X POST http://127.0.0.1:8011/query \
  -H 'content-type: application/json' \
  -d '{"question":"How early should I request vacation?"}'
```

`SEED_KNOWLEDGE_BASE=true`이면 안정적인 `chunk_id`로 작은 corpus를 upsert합니다. 반복 시작 시 동일 ID를 사용해 중복 누적을 피합니다. OpenAI 호출은 네트워크와 비용이 발생할 수 있습니다.

live retrieval은 relevance score `0.35` 이상인 문서만 workflow에 전달합니다. Week 1은 근거가 없으면 `insufficient_evidence`, Week 2는 모델 planner를 호출하지 않고 `needs_more_information`으로 종료합니다. 이 임계값은 학습용 작은 corpus의 시작점이며 실제 자료로 확장할 때 별도 retrieval evaluation으로 다시 조정해야 합니다.

### 2-5. 중지·초기화와 문제 해결

```bash
# 컨테이너 중지(데이터 유지)
docker compose down

# 로컬 실습 DB volume까지 삭제(파괴적 초기화)
docker compose down -v
```

- **DB가 unhealthy:** `docker compose logs pgvector`와 포트 `6024` 충돌을 확인합니다.
- **포트 충돌:** `.env`의 `POSTGRES_PORT`와 `DATABASE_URL` port를 함께 변경합니다.
- **인증 실패:** `.env`의 `POSTGRES_*`와 `DATABASE_URL` 사용자·DB 이름이 일치하는지 확인합니다.
- **OpenAI 인증 실패:** key를 응답이나 log에 출력하지 말고 환경변수 주입 여부만 확인합니다.
- **기존 volume 때문에 init.sql이 재실행되지 않음:** 학습 데이터 삭제를 수용할 때만 `docker compose down -v` 후 재기동합니다.

> 현재 Hermes 실행 환경에는 Compose v2 plugin과 Docker daemon이 없어 이 문서의 컨테이너 기동은 검증하지 못했습니다. Compose artifact·환경값·SQL은 정적으로 검증하며, fixture test와 Notebook은 Docker 없이 검증합니다.

## 3. Notebook 실행

13개 Notebook은 canonical `app.py`를 import하지 않습니다. 각 Notebook 안에서 작은 모델·문서·state·node·edge·router·guard를 직접 정의하고 중간 결과와 실패 경계를 관찰합니다. 외부 API/DB 없이 실행되며, live OpenAI+pgvector의 역할과 데이터 흐름은 교육용 소형 fixture로 재현합니다. `MiniEmbedding` 같은 fixture는 공식 adapter 인터페이스의 완전한 대체 구현이 아닙니다.

```bash
mkdir -p /tmp/agent-workflow-notebooks
for notebook in week*/notebooks/*.ipynb; do
  APP_MODE=fixture PYTHONPATH="$PWD" .venv/bin/jupyter nbconvert --to notebook --execute \
    --ExecutePreprocessor.timeout=90 \
    --output-dir /tmp/agent-workflow-notebooks "$notebook"
done
```

## 안전 경계

- synthetic policy·playbook·incident만 사용합니다.
- Week 1은 휴가를 신청·승인하지 않습니다.
- Week 2는 환불·계정 변경·티켓 종료를 실행하지 않습니다.
- Week 3은 subprocess/Kubernetes client가 없으며 모든 경로에서 `executed_commands: []`입니다.
- `dry_run=True`만 신뢰하지 않고 관찰 전용 명령 allowlist를 다시 검사합니다.
- SEV1/SEV2는 사람이 검토하며, 승인 packet은 실행 완료를 뜻하지 않습니다.
