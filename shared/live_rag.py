"""OpenAI and pgvector services used only when ``APP_MODE=live``.

The fixture applications deliberately import this module without initializing any
network client.  That keeps lessons and their tests reproducible without an API
key or a running database.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from typing import Iterable
from uuid import NAMESPACE_URL, uuid5

from langchain_core.documents import Document


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
            min_relevance = float(os.getenv("RAG_MIN_RELEVANCE", "0.55"))
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
    return [document for document, score in results if score >= settings.min_relevance]


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
