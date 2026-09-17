# RAG 실행 흐름: 아주 쉽게 보기

이 프로젝트는 **문서를 찾아서, 그 문서만 보고 답하는 연습**입니다.

아래에서 `문서 상자`는 pgvector DB이고, `선생님`은 OpenAI API라고 생각하면 됩니다.

```text
처음 한 번: 문서 넣기

knowledge/week1/*.md ──┐
knowledge/week2/*.md ──┼─> shared/ingest.py ─> OpenAI (문서를 숫자 카드로 바꿈)
knowledge/week3/*.md ──┘                                  │
                                                           v
                                           Docker 안 pgvector DB (문서 상자)

질문할 때: 문서를 찾아 답하기

브라우저
  │  http://localhost:8501
  v
Streamlit UI
  │  HTTP 요청 (Week 1: 8011 / Week 2: 8012 / Week 3: 8013)
  v
FastAPI + LangGraph
  │  1. 질문을 OpenAI로 숫자 카드로 바꿈
  │  2. pgvector 문서 상자에서 가장 비슷한 카드 찾기
  │  3. 찾은 문서 조각만 OpenAI에게 보여 주고 답을 부탁함
  v
Streamlit UI ──> 답변 + 출처(문서 ID, 청크 ID)를 브라우저에 표시
```

## 등장인물 네 명

| 누구 | 아주 쉬운 설명 | 이 프로젝트에서 하는 일 |
|---|---|---|
| Docker | DB를 담아 두는 도시락통 | PostgreSQL과 pgvector를 컴퓨터 안에서 실행한다. |
| pgvector DB | 문서 조각을 넣어 두는 상자 | 문서 본문, 메타데이터, 임베딩 숫자 카드를 저장하고 비슷한 문서를 찾는다. |
| FastAPI | 주문을 받아 주는 직원 | UI의 질문을 받고, 검색·답변 과정을 실행해 JSON으로 돌려준다. |
| Streamlit | 사람이 보는 화면 | 질문을 입력받고 FastAPI의 결과를 화면에 보여 준다. DB에 직접 접속하지 않는다. |

## 중요한 약속

- 브라우저와 Streamlit은 DB에 직접 접속하지 않습니다.
- OpenAI API 키와 DB 비밀번호는 FastAPI/적재기 프로세스 안에서만 사용합니다. 화면에는 전체 값을 보여 주지 않습니다.
- `knowledge/`의 Markdown 파일은 **적재할 때** 읽습니다. 질의할 때는 그 복사본인 pgvector DB를 검색합니다.
- `APP_MODE=fixture`는 연습용 가짜 문서를 쓰는 모드입니다. 실제 문서 검색은 `APP_MODE=live`에서만 합니다.

## 실행 순서

1. `.env`에 실제 `OPENAI_API_KEY`, `APP_MODE=live`, DB 설정을 넣습니다.
2. `docker compose --env-file .env -f infra/compose.pgvector.yml up -d`로 문서 상자를 켭니다.
3. `python -m shared.ingest --week weekN`으로 해당 Week 문서를 상자에 넣습니다.
4. Week FastAPI를 `--env-file .env`와 함께 실행합니다.
5. Streamlit을 실행하고 브라우저에서 질문합니다.

자세한 실행 파일 목록은 [Week 1](week1-running-files.md), [Week 2](week2-running-files.md), [Week 3](week3-running-files.md) 문서를 봅니다.
