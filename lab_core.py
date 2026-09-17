"""Shared fixture and live adapters for the three learning applications."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Iterable

from langchain_core.documents import Document


def tokens(text: str) -> set[str]:
    stopwords = {"the", "is", "a", "an", "to", "or", "and", "what", "how", "should", "i"}
    return {
        token.lower()
        for token in re.findall(r"[A-Za-z0-9가-힣]+", text)
        if len(token) > 1 and token.lower() not in stopwords
    }


def resolve_mode(explicit_mode: str | None = None) -> str:
    mode = explicit_mode or os.getenv("APP_MODE", "fixture")
    if mode not in {"fixture", "live"}:
        raise ValueError("APP_MODE must be either 'fixture' or 'live'")
    return mode


class FixtureRetriever:
    """Small deterministic retriever used by tests and credential-free notebooks."""

    def __init__(self, documents: Iterable[Document]):
        self.documents = list(documents)

    def search(
        self, query: str, *, k: int = 3, filter: dict[str, Any] | None = None
    ) -> list[Document]:
        query_tokens = tokens(query)
        candidates = self.documents
        if filter:
            candidates = [
                document
                for document in candidates
                if all(document.metadata.get(key) == value for key, value in filter.items())
            ]
        ranked = sorted(
            ((len(query_tokens & tokens(document.page_content)), document) for document in candidates),
            key=lambda item: item[0],
            reverse=True,
        )
        return [document for score, document in ranked[:k] if score > 0]


@dataclass(frozen=True)
class LiveSettings:
    openai_api_key: str
    database_url: str
    chat_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    seed_knowledge_base: bool = True

    @classmethod
    def from_env(cls) -> "LiveSettings":
        missing = [name for name in ("OPENAI_API_KEY", "DATABASE_URL") if not os.getenv(name)]
        if missing:
            raise RuntimeError(f"live mode requires {', '.join(missing)}")
        return cls(
            openai_api_key=os.environ["OPENAI_API_KEY"],
            database_url=os.environ["DATABASE_URL"],
            chat_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
            embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            seed_knowledge_base=os.getenv("SEED_KNOWLEDGE_BASE", "true").lower() in {"1", "true", "yes"},
        )


class PGVectorRetriever:
    def __init__(self, store: Any, *, min_relevance_score: float = 0.35):
        self.store = store
        self.min_relevance_score = min_relevance_score

    def search(
        self, query: str, *, k: int = 3, filter: dict[str, Any] | None = None
    ) -> list[Document]:
        ranked = self.store.similarity_search_with_relevance_scores(
            query,
            k=k,
            filter=filter,
        )
        return [
            document
            for document, score in ranked
            if score >= self.min_relevance_score
        ]


class OpenAIModel:
    def __init__(self, model: Any):
        self.model = model

    def text(self, prompt: str) -> str:
        return str(self.model.invoke(prompt).content)

    def structured(self, schema: type, prompt: str) -> Any:
        return self.model.with_structured_output(schema).invoke(prompt)


def build_live_adapters(
    *, collection_name: str, documents: list[Document]
) -> tuple[PGVectorRetriever, OpenAIModel]:
    """Build real OpenAI + PostgreSQL/pgvector adapters lazily for live mode."""
    settings = LiveSettings.from_env()
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from langchain_postgres import PGVector
    embeddings = OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )
    store = PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=settings.database_url,
        use_jsonb=True,
    )
    if settings.seed_knowledge_base:
        ids = [str(document.metadata["chunk_id"]) for document in documents]
        store.add_documents(documents=documents, ids=ids)
    model = ChatOpenAI(model=settings.chat_model, temperature=0, api_key=settings.openai_api_key)
    return PGVectorRetriever(store), OpenAIModel(model)


def citations(documents: Iterable[Document]) -> list[dict[str, str]]:
    return [
        {
            "document_id": str(document.metadata["document_id"]),
            "chunk_id": str(document.metadata["chunk_id"]),
        }
        for document in documents
    ]


def source_context(documents: Iterable[Document]) -> str:
    return "\n".join(f"[{document.metadata['chunk_id']}] {document.page_content}" for document in documents)
