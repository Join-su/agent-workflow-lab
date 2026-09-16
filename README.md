# RAG Multi-Agent Weekly Labs

매주 독립 프로젝트 하나를 완성 코드부터 실행한 뒤, 같은 주 폴더 안의 Notebook으로 FastAPI·RAG·멀티 에이전트·배포를 분해해 실습하는 저장소입니다.

## 폴더를 여는 순서

```text
week1/  # 난이도 1/5 — 규정 Q&A
week2/  # 난이도 2/5 — 출장비 증빙 검토
week3/  # 난이도 3/5 — 변경 요청 안전 검토
```

각 `weekN/` 폴더는 자체적으로 다음을 포함합니다.

```text
app.py · tests/ · notebooks/ · deploy/ · README.md
```

## 전체 테스트

```bash
uv sync
.venv/bin/python -m unittest discover -s . -p 'test_*.py' -v
```

## 주차별 실행

```bash
.venv/bin/uvicorn week1.app:app --port 8011
.venv/bin/uvicorn week2.app:app --port 8012
.venv/bin/uvicorn week3.app:app --port 8013
```

## 학습 원칙

- 난이도는 1~5 척도 중 `1 → 2 → 3`으로 한 주마다 한 단계 증가합니다.
- 실제 업무 문서·개인정보·쓰기 권한 Tool은 사용하지 않습니다.
- 근거 부족은 `clarify`, 위험·권한 문제는 `human_review`로 보류합니다.
- `.env`와 실제 API key는 Git에 커밋하지 않습니다.

Docker Compose 파일은 주차별 `weekN/deploy/`에 있습니다. 현재 서버에는 Compose plugin이 없어 컨테이너 기동은 별도 Docker 환경에서 확인해야 합니다.
