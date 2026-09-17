"""OpenAI and pgvector services used only when ``APP_MODE=live``.

The fixture applications deliberately import this module without initializing any
network client.  That keeps lessons and their tests reproducible without an API
key or a running database.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import lru_cache
import os
import sys
from typing import Iterable
from uuid import NAMESPACE_URL, uuid5

from langchain_core.documents import Document


# ``langchain-postgres`` uses psycopg's async connection internally, even from
# its synchronous PGEngine helpers. Psycopg cannot run on Windows' default
# Proactor loop, so choose the selector loop before a database engine is made.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class LiveRagError(RuntimeError):
    """A configuration, dependency, or remote-service error in live mode."""


class LiveRagConfigurationError(LiveRagError):
    """Raised before attempting a live request with incomplete configuration."""


def is_live_mode() -> bool:
    """Return whether the process is explicitly configured for live RAG."""
    return os.getenv("APP_MODE", "fixture").strip().lower() == "live"


WEEK_COLLECTIONS = {
    "week1": "agent_workflow_week1",
    "week2": "agent_workflow_week2",
    "week3": "agent_workflow_week3",
}


@dataclass(frozen=True)
class LiveRagSettings:
    api_key: str
    database_url: str
    chat_model: str
    embedding_model: str
    embedding_dimensions: int
    retrieval_k: int
    min_relevance: float

    @classmethod
    def from_environment(cls) -> "LiveRagSettings":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        database_url = os.getenv("DATABASE_URL", "").strip()
        missing = [
            name
            for name, value in (("OPENAI_API_KEY", api_key), ("DATABASE_URL", database_url))
            if not value
        ]
        if missing:
            raise LiveRagConfigurationError(
                "Live RAG를 사용하려면 환경 변수 " + ", ".join(missing) + " 설정이 필요합니다."
            )

        try:
            retrieval_k = int(os.getenv("RAG_RETRIEVAL_K", "4"))
            min_relevance = float(os.getenv("RAG_MIN_RELEVANCE", "0.25"))
            embedding_dimensions = int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "1536"))
        except ValueError as error:
            raise LiveRagConfigurationError(
                "RAG_RETRIEVAL_K와 OPENAI_EMBEDDING_DIMENSIONS는 정수이고 "
                "RAG_MIN_RELEVANCE는 숫자여야 합니다."
            ) from error
        if retrieval_k < 1 or embedding_dimensions < 1 or not 0 <= min_relevance <= 1:
            raise LiveRagConfigurationError(
                "RAG_RETRIEVAL_K와 OPENAI_EMBEDDING_DIMENSIONS는 양수이고 "
                "RAG_MIN_RELEVANCE는 0~1 범위여야 합니다."
            )

        return cls(
            api_key=api_key,
            database_url=database_url,
            chat_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip(),
            embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip(),
            embedding_dimensions=embedding_dimensions,
            retrieval_k=retrieval_k,
            min_relevance=min_relevance,
        )


def _imports():
    """Load optional live dependencies only after live mode has been selected."""
    try:
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from langchain_postgres import PGEngine, PGVectorStore
    except ImportError as error:
        raise LiveRagError(
            "Live RAG 의존성이 없습니다. requirements.txt를 다시 설치하세요."
        ) from error
    return ChatOpenAI, OpenAIEmbeddings, PGEngine, PGVectorStore


@lru_cache(maxsize=8)
def _vector_store(collection_name: str):
    settings = LiveRagSettings.from_environment()
    _, OpenAIEmbeddings, PGEngine, PGVectorStore = _imports()
    embeddings = OpenAIEmbeddings(
        api_key=settings.api_key,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
    try:
        engine = PGEngine.from_connection_string(url=settings.database_url)
        return PGVectorStore.create_sync(
            engine=engine,
            table_name=collection_name,
            embedding_service=embeddings,
        )
    except Exception as error:  # The driver exposes several database exception types.
        raise LiveRagError("Live RAG용 PostgreSQL/pgvector에 연결할 수 없습니다.") from error


def retrieve_documents(collection_name: str, query: str) -> list[Document]:
    """Return only sufficiently relevant live documents for a query.

    An empty result is intentional: callers must end safely instead of asking an
    LLM to answer without evidence.
    """
    documents, _ = retrieve_documents_with_trace(collection_name, query)
    return documents


def retrieve_documents_with_trace(
    collection_name: str, query: str
) -> tuple[list[Document], list[dict[str, str | float | bool]]]:
    """Search pgvector and return safe retrieval evidence for the API response.

    The trace intentionally contains document identifiers and relevance scores,
    never an embedding vector or an API credential.
    """
    settings = LiveRagSettings.from_environment()
    try:
        results = _vector_store(collection_name).similarity_search_with_relevance_scores(
            query,
            k=settings.retrieval_k,
        )
    except LiveRagError:
        raise
    except Exception as error:
        raise LiveRagError("pgvector 문서 컬렉션을 검색할 수 없습니다.") from error
    trace: list[dict[str, str | float | bool]] = []
    accepted: list[Document] = []
    for document, score in results:
        relevance_score = float(score)
        selected = relevance_score >= settings.min_relevance
        trace.append(
            {
                "document_id": str(document.metadata.get("document_id", "unknown")),
                "chunk_id": str(document.metadata.get("chunk_id", "unknown")),
                "relevance_score": round(relevance_score, 4),
                "selected": selected,
            }
        )
        if selected:
            accepted.append(document)
    return accepted, trace


def collection_diagnostics(
    collection_name: str, *, include_chunks: bool = False
) -> dict[str, object]:
    """Return a deliberately limited, read-only view of a live collection."""
    if collection_name not in WEEK_COLLECTIONS.values():
        raise LiveRagConfigurationError("허용되지 않은 pgvector 컬렉션입니다.")
    if not is_live_mode():
        return {
            "mode": "fixture",
            "api_key_prefix": None,
            "collection": collection_name,
            "chunk_count": 0,
            "chunks": [],
        }

    settings = LiveRagSettings.from_environment()
    try:
        import psycopg
        from psycopg import sql

        connection_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        with psycopg.connect(connection_url) as connection, connection.cursor() as cursor:
            table = sql.Identifier(collection_name)
            cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(table))
            chunk_count = int(cursor.fetchone()[0])
            chunks: list[dict[str, object]] = []
            if include_chunks:
                cursor.execute(
                    sql.SQL(
                        "SELECT langchain_metadata->>'document_id', "
                        "langchain_metadata->>'chunk_id', "
                        "langchain_metadata->>'source', "
                        "length(content), vector_dims(embedding), left(content, 700) "
                        "FROM {} ORDER BY langchain_metadata->>'chunk_id'"
                    ).format(table)
                )
                chunks = [
                    {
                        "document_id": row[0] or "unknown",
                        "chunk_id": row[1] or "unknown",
                        "source": row[2] or "unknown",
                        "characters": int(row[3]),
                        "embedding_dimensions": int(row[4]),
                        "content_preview": row[5],
                    }
                    for row in cursor.fetchall()
                ]
    except Exception as error:
        raise LiveRagError("pgvector 저장 문서 정보를 조회할 수 없습니다.") from error

    return {
        "mode": "live",
        "api_key_prefix": f"{settings.api_key[:5]}…",
        "chat_model": settings.chat_model,
        "embedding_model": settings.embedding_model,
        "min_relevance": settings.min_relevance,
        "collection": collection_name,
        "chunk_count": chunk_count,
        "chunks": chunks,
    }


def initialize_collection(collection_name: str, *, reset: bool = False) -> None:
    """Create a pgvector table; reset it only when explicitly requested."""
    settings = LiveRagSettings.from_environment()
    _, _, PGEngine, _ = _imports()
    try:
        engine = PGEngine.from_connection_string(url=settings.database_url)
        engine.init_vectorstore_table(
            table_name=collection_name,
            vector_size=settings.embedding_dimensions,
            overwrite_existing=reset,
        )
    except Exception as error:
        # PostgreSQL reports an existing table while preserving it.  Other failures
        # (credentials, unavailable DB, or a vector-size migration) must remain visible.
        if not reset and "already exists" in str(error).lower():
            return
        raise LiveRagError("PostgreSQL/pgvector 컬렉션을 초기화할 수 없습니다.") from error


def ingest_documents(
    collection_name: str, documents: Iterable[Document], *, reset: bool = False
) -> int:
    """Embed and upsert documents into a named pgvector collection."""
    materialized = list(documents)
    if not materialized:
        return 0
    for index, document in enumerate(materialized, start=1):
        document.metadata.setdefault("document_id", collection_name)
        document.metadata.setdefault("chunk_id", f"{collection_name}-{index:03d}")
    initialize_collection(collection_name, reset=reset)
    ids = [
        str(
            uuid5(
                NAMESPACE_URL,
                f"{collection_name}:{document.metadata['document_id']}:"
                f"{document.metadata['chunk_id']}:{document.page_content}",
            )
        )
        for document in materialized
    ]
    try:
        _vector_store.cache_clear()
        _vector_store(collection_name).add_documents(materialized, ids=ids)
    except LiveRagError:
        raise
    except Exception as error:
        raise LiveRagError("문서를 임베딩하여 pgvector에 저장할 수 없습니다.") from error
    return len(materialized)


def generate_grounded_text(
    question: str,
    evidence: list[Document],
    *,
    task: str,
) -> str:
    """Generate a concise answer that is limited to the supplied evidence."""
    if not evidence:
        raise LiveRagError("근거 문서 없이 답변을 생성할 수 없습니다.")

    settings = LiveRagSettings.from_environment()
    ChatOpenAI, _, _, _ = _imports()
    excerpts = "\n\n".join(
        f"[document_id={doc.metadata.get('document_id', 'unknown')}; "
        f"chunk_id={doc.metadata.get('chunk_id', 'unknown')}]\n{doc.page_content}"
        for doc in evidence
    )
    prompt = (
        "You are a careful Korean enterprise assistant. "
        "Use only the evidence excerpts below. Do not invent policy, approval, or facts. "
        "If the excerpts do not answer the request, reply exactly: 근거가 부족합니다.\n\n"
        f"Task: {task}\nRequest: {question}\n\nEvidence:\n{excerpts}"
    )
    try:
        response = ChatOpenAI(
            api_key=settings.api_key,
            model=settings.chat_model,
            temperature=0,
        ).invoke(prompt)
    except Exception as error:
        raise LiveRagError("OpenAI 답변 생성에 실패했습니다.") from error
    content = response.content
    if isinstance(content, str):
        return content.strip()
    return str(content).strip()


def citations_for(documents: Iterable[Document]) -> list[dict[str, str]]:
    """Create the stable citation payload used by all three API contracts."""
    return [
        {
            "document_id": str(document.metadata.get("document_id", "unknown")),
            "chunk_id": str(document.metadata.get("chunk_id", "unknown")),
        }
        for document in documents
    ]
