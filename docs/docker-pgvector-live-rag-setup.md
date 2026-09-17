# Windows에서 Docker Desktop·PostgreSQL·pgvector로 Live RAG 환경 만들기

이 문서는 `agent-workflow-lab`의 fixture 기반 예제를 실제 문서 검색과 LLM API를 사용하는 **live RAG 환경**으로 전환하기 위한 사전 설정 안내서입니다.

대상 환경은 Windows 명령 프롬프트(cmd.exe)입니다. PostgreSQL을 Windows에 직접 설치하지 않고, Docker Desktop 안에서 PostgreSQL과 pgvector를 함께 실행합니다.

## 1. 완성 후 구조

```text
Streamlit UI
  → FastAPI HTTP API
    → LangGraph workflow
      ├─ OpenAI API: 분류·답변·계획 생성
      └─ PostgreSQL + pgvector: 문서 조각·임베딩·메타데이터 검색
```

PostgreSQL+pgvector는 다음을 영구 보관합니다.

- 주차별 예제 문서에서 나눈 문서 조각
- 각 조각의 embedding 벡터
- 문서 이름·주차·분류 등 검색 필터용 메타데이터
- 답변에 표시할 citation의 원본 식별자

`fixture` 모드는 API 키나 DB 없이 테스트·Notebook용으로 유지하고, `live` 모드만 실제 OpenAI API와 pgvector를 사용합니다.

## 2. 시작 전 확인

명령 프롬프트를 열고 다음을 실행합니다.

```bat
wsl --version
wsl --status
docker version
docker compose version
```

처음 두 `wsl` 명령은 WSL 2가 준비됐는지, 마지막 두 명령은 Docker Desktop과 Compose 플러그인이 준비됐는지 확인합니다.

이 문서를 작성한 시점의 PC에서는 `docker` 명령이 없었습니다. Docker Desktop 설치를 마친 뒤 이 단계를 다시 실행해야 합니다.

## 3. Docker Desktop과 WSL 2 설치

1. [Docker Desktop for Windows 공식 설치 문서](https://docs.docker.com/desktop/setup/install/windows-install/)에서 설치 프로그램을 내려받습니다.
2. 관리자 권한 명령 프롬프트를 열고 WSL이 없다면 다음을 실행한 뒤 Windows를 재시작합니다.

   ```bat
   wsl --install
   ```

   WSL이 이미 있다면 최신화합니다.

   ```bat
   wsl --update
   ```

3. `Docker Desktop Installer.exe`를 실행합니다. 일반적인 개인 개발 환경에서는 **per-user 설치**와 **Use WSL 2 instead of Hyper-V**를 선택합니다.
4. 설치 후 Docker Desktop을 시작합니다. `Settings → General`에서 **Use the WSL 2 based engine**이 활성화돼 있는지 확인하고 적용합니다.
5. 새 명령 프롬프트 창을 연 뒤 아래 명령이 모두 성공하는지 확인합니다.

   ```bat
   docker version
   docker compose version
   docker run --rm hello-world
   ```

`hello-world` 출력에 성공 메시지가 나오면 Docker가 이미지를 내려받고 컨테이너를 실행할 수 있는 상태입니다.

> Docker Desktop은 조직 규모와 사용 용도에 따라 구독 조건이 달라질 수 있으므로, 조직에서 사용할 때는 Docker의 라이선스 정책을 확인합니다.

## 4. 프로젝트 비밀값 준비

프로젝트 루트의 `.env`는 Git에서 제외돼 있습니다. API 키·비밀번호를 소스, Notebook, README, 채팅에 기록하지 않습니다.

live 구현이 추가된 뒤 `.env`에는 아래 항목이 필요합니다.

```dotenv
# 실제 값을 채운다. 따옴표와 공백을 넣지 않는다.
OPENAI_API_KEY=replace-with-your-key
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536

# 영문·숫자·기호를 섞어 길게 만든다. 실제 값은 저장소에 커밋하지 않는다.
POSTGRES_PASSWORD=replace-with-a-strong-local-password

# 애플리케이션이 사용할 SQLAlchemy/psycopg 연결 문자열
DATABASE_URL=postgresql+psycopg://app_user:replace-with-a-strong-local-password@127.0.0.1:5432/agent_workflow

# fixture 또는 live. 실 API/DB 사용은 live일 때만 한다.
APP_MODE=live
RAG_RETRIEVAL_K=4
RAG_MIN_RELEVANCE=0.55
```

현재 `.env`에 있는 `MODEL_API_KEY`는 어떤 API 제공자용인지 명확하지 않습니다. 아래 live 구현 단계 전에 **OpenAI 공식 API를 사용할지**, 혹은 OpenAI 호환 서비스라면 **base URL과 모델명**을 확정합니다. 이 안내서는 OpenAI 공식 API를 기준으로 작성합니다.

## 5. pgvector Compose 파일 만들기

live 구현 단계에서 프로젝트 루트에 `infra/compose.pgvector.yml` 파일을 만들고, 다음 내용을 저장합니다. 이미지 태그는 재현성을 위해 PostgreSQL 16과 pgvector 0.8.6으로 고정합니다.

```yaml
services:
  pgvector:
    image: pgvector/pgvector:0.8.6-pg16-bookworm
    container_name: agent-workflow-pgvector
    environment:
      POSTGRES_DB: agent_workflow
      POSTGRES_USER: app_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in .env}
    ports:
      # 외부 네트워크에는 열지 않고 이 PC에서만 접근한다.
      - "127.0.0.1:5432:5432"
    volumes:
      - pgvector_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app_user -d agent_workflow"]
      interval: 5s
      timeout: 3s
      retries: 20

volumes:
  pgvector_data:
```

`pgvector/pgvector` 이미지는 PostgreSQL에 pgvector 확장을 포함합니다. 컨테이너를 지워도 named volume을 지우지 않는 한 데이터는 유지됩니다.

## 6. DB 시작과 상태 확인

프로젝트 루트에서 실행합니다.

```bat
docker compose --env-file .env -f infra/compose.pgvector.yml up -d
docker compose --env-file .env -f infra/compose.pgvector.yml ps
docker compose --env-file .env -f infra/compose.pgvector.yml logs -f pgvector
```

`ps`의 상태가 `healthy`가 될 때까지 기다립니다. 로그를 계속 보는 명령은 `Ctrl+C`로 종료해도 컨테이너는 계속 실행됩니다.

다른 터미널에서 PostgreSQL과 pgvector 확장을 확인합니다.

```bat
docker exec -it agent-workflow-pgvector psql -U app_user -d agent_workflow -c "SELECT version();"
docker exec -it agent-workflow-pgvector psql -U app_user -d agent_workflow -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker exec -it agent-workflow-pgvector psql -U app_user -d agent_workflow -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

마지막 명령이 `vector` 행을 반환하면 준비가 완료된 것입니다. `CREATE EXTENSION IF NOT EXISTS vector`는 안전하게 반복 실행할 수 있습니다.

## 7. 간단한 벡터 SQL 검증

애플리케이션을 붙이기 전, pgvector 타입을 PostgreSQL이 인식하는지 확인합니다.

```bat
docker exec -it agent-workflow-pgvector psql -U app_user -d agent_workflow -c "SELECT '[1,2,3]'::vector <=> '[1,2,3]'::vector AS cosine_distance;"
```

결과가 `0`이면 동일한 벡터 간 cosine distance 계산이 동작한 것입니다. 실제 embedding 차원은 사용하는 OpenAI embedding 모델에 따라 달라지며, 애플리케이션의 `langchain-postgres`가 테이블과 차원을 관리합니다. 이 수동 예시는 pgvector 확장 자체의 확인용입니다.

## 8. 앱 적용 순서

live 앱 코드가 추가되면 아래 순서로 실행합니다.

1. `.env`에서 `OPENAI_API_KEY`, `OPENAI_MODEL`, `POSTGRES_PASSWORD`, `DATABASE_URL`, `APP_MODE=live`를 확인합니다.
2. Compose로 pgvector가 `healthy`인지 확인합니다.
3. 주차별 예제 정책 문서를 적재합니다. 적재기는 문서를 읽고, 분할하고, embedding을 생성하고, 주차별 pgvector table에 저장합니다. 일반 적재는 같은 청크 ID를 upsert하며 기존 table을 지우지 않습니다.

   ```bat
   # live 구현 후 제공될 명령 예시
   .venv\Scripts\python.exe -m shared.ingest --week week1
   .venv\Scripts\python.exe -m shared.ingest --week week2
   .venv\Scripts\python.exe -m shared.ingest --week week3
   ```

   embedding 모델 또는 차원을 바꾼 경우에는 table schema를 다시 만들어야 합니다. 아래 명령은 해당 주차의 저장된 문서를 삭제하므로, 의도적으로 초기화할 때만 사용합니다.

   ```bat
   .venv\Scripts\python.exe -m shared.ingest --week week1 --reset
   ```

4. FastAPI 서버를 실행합니다.

   ```bat
   .venv\Scripts\uvicorn.exe week1.app:app --port 8011
   .venv\Scripts\uvicorn.exe week2.app:app --port 8012
   .venv\Scripts\uvicorn.exe week3.app:app --port 8013
   ```

5. 각 `http://127.0.0.1:801N/docs`에서 API를 확인합니다.
6. Streamlit UI를 별도 터미널에서 실행합니다.

   ```bat
   .venv\Scripts\streamlit.exe run streamlit_app.py
   ```

Streamlit은 FastAPI의 HTTP API를 호출해야 합니다. UI가 Python 함수를 직접 호출하면 API·인증·오류 처리·배포 경계를 검증할 수 없으므로 완성 앱 구조에 맞지 않습니다.

## 9. 정상 동작 기준

아래 조건을 모두 만족해야 live RAG가 동작하는 것입니다.

- `docker compose ... ps`에서 DB가 `healthy`
- `vector` 확장이 설치됨
- 주차별 문서 적재 시 collection별 문서 조각 수가 기록됨
- 지원되는 질문은 실제 OpenAI API 응답과 citation을 반환함
- 근거가 부족한 질문은 답변을 꾸며내지 않고 `insufficient_evidence`로 종료함
- Streamlit이 FastAPI를 HTTP로 호출하며, FastAPI가 DB/LLM 오류를 한국어로 구분해 반환함
- fixture 테스트와 live smoke test 결과를 혼동하지 않음

## 10. 중지·재시작·데이터 초기화

```bat
# 컨테이너만 중지한다. 데이터 volume은 유지된다.
docker compose --env-file .env -f infra/compose.pgvector.yml stop

# 컨테이너와 네트워크를 내린다. 데이터 volume은 유지된다.
docker compose --env-file .env -f infra/compose.pgvector.yml down

# 다시 시작한다.
docker compose --env-file .env -f infra/compose.pgvector.yml up -d
```

아래 명령은 데이터베이스 volume을 삭제합니다. 적재한 문서와 embedding이 모두 사라지므로, 정말 초기화가 필요할 때만 실행합니다.

```bat
docker compose --env-file .env -f infra/compose.pgvector.yml down -v
```

초기화 후에는 문서를 다시 적재해야 합니다.

## 11. 자주 발생하는 문제

| 증상 | 원인과 조치 |
|---|---|
| `docker`를 찾을 수 없음 | Docker Desktop을 설치·시작한 뒤 새 명령 프롬프트를 엽니다. |
| Docker Desktop이 시작되지 않음 | `wsl --status`, `wsl --update`를 확인하고 재시작합니다. BIOS/UEFI 가상화 설정도 확인합니다. |
| 5432 포트를 사용할 수 없음 | `netstat -ano | findstr :5432`로 기존 PostgreSQL을 확인합니다. 충돌하면 Compose의 호스트 포트를 `127.0.0.1:5433:5432`로 바꾸고 `DATABASE_URL`도 5433으로 바꿉니다. |
| `vector` 확장이 없음 | `postgres` 기본 이미지가 아니라 `pgvector/pgvector` 이미지를 사용했는지 확인하고, `CREATE EXTENSION IF NOT EXISTS vector`를 실행합니다. |
| DB는 healthy지만 앱 연결 실패 | `.env`의 비밀번호와 `DATABASE_URL` 사용자·포트·DB명을 비교합니다. `127.0.0.1`을 사용해 로컬 연결임을 명확히 합니다. |
| 실제 답변이 항상 같음 | 앱이 `APP_MODE=fixture`이거나 문서 적재가 완료되지 않은 상태입니다. API 로그와 collection 적재 수를 확인합니다. |
| OpenAI 인증 실패 | 키 이름·활성 상태·프로젝트 권한·결제 상태를 확인합니다. 키 값은 로그에 출력하지 않습니다. |

## 12. 참고 문서

- [Docker Desktop Windows 설치 공식 문서](https://docs.docker.com/desktop/setup/install/windows-install/)
- [Docker Desktop WSL 2 backend 공식 문서](https://docs.docker.com/desktop/features/wsl/)
- [pgvector 공식 README와 Docker 이미지 태그](https://github.com/pgvector/pgvector#docker)
- [pgvector Docker Hub 이미지](https://hub.docker.com/r/pgvector/pgvector)
