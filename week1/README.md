# Week 1 — 규정 Q&A (난이도 1/5)

이 폴더만 열면 해당 주의 **완성 코드·테스트·Notebook·Docker 배포 파일**을 모두 볼 수 있습니다.

```text
week1/
├── app.py                 # 완성된 FastAPI + RAG + Agent 구현
├── tests/test_api.py      # 핵심 동작 자동 테스트
├── notebooks/             # FastAPI → RAG → Agent → Deployment 실습
├── deploy/                # Dockerfile, compose.yaml
└── README.md              # 이 주의 실행·완료 기준
```

## Agent 흐름

```text
Retriever → Answer
```

## 먼저 전체 코드를 실행

저장소 루트에서 실행합니다.

```bash
uv sync
.venv/bin/uvicorn week1.app:app --port 8011
.venv/bin/python -m unittest week1.tests.test_api -v
```

## Notebook 실습 순서

1. `notebooks/01_fastapi.ipynb`
2. `notebooks/02_rag.ipynb`
3. `notebooks/03_agents.ipynb`
4. `notebooks/04_deployment.ipynb`

## Docker Compose

```bash
cp .env.example .env
cd week1/deploy
docker compose -f compose.yaml up --build
```

현재 서버에는 Docker Compose plugin이 없으므로 Compose 기동은 별도 Docker 환경에서 확인해야 합니다.
