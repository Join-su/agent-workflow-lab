"""CLI for loading weekly Markdown policy sources into live pgvector."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from shared.live_rag import WEEK_COLLECTIONS, LiveRagError, ingest_documents, is_live_mode


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = REPOSITORY_ROOT / "knowledge"
SPLITTER = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
CATEGORY_PATTERN = re.compile(r"^카테고리:\s*([A-Za-z_]+)\s*$", re.MULTILINE)
DEFAULT_CATEGORY = "other"


def document_category(markdown: str) -> str:
    """Read the reviewable category header a retrieval filter can match on.

    A document without the header stays in the catch-all category instead of
    silently joining whichever category is being searched.
    """
    match = CATEGORY_PATTERN.search(markdown)
    return match.group(1) if match else DEFAULT_CATEGORY


def markdown_documents(week: str) -> list[Document]:
    """Read stable, reviewable Markdown sources for a single weekly collection."""
    source_directory = KNOWLEDGE_ROOT / week
    source_files = sorted(source_directory.glob("*.md"))
    if not source_files:
        raise LiveRagError(f"No Markdown source documents found in {source_directory}.")

    documents: list[Document] = []
    for source_file in source_files:
        markdown = source_file.read_text(encoding="utf-8")
        source = Document(
            page_content=markdown,
            metadata={
                "document_id": source_file.stem,
                "source": source_file.relative_to(KNOWLEDGE_ROOT).as_posix(),
                "week": week,
                # Week 2 filters retrieval by this field; other weeks carry it unused.
                "category": document_category(markdown),
            },
        )
        for index, chunk in enumerate(SPLITTER.split_documents([source]), start=1):
            chunk.metadata["chunk_id"] = f"{source_file.stem}-{index:03d}"
            documents.append(chunk)
    return documents


def main() -> int:
    # This CLI is normally launched as ``python -m shared.ingest``. Unlike
    # Uvicorn's ``--env-file`` option, Python does not load .env by itself.
    # Keep this local to the command so importing the RAG library still has a
    # deterministic fixture default for tests.
    load_dotenv(REPOSITORY_ROOT / ".env", override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", choices=sorted(WEEK_COLLECTIONS), required=True)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate this week's vector table before ingestion.",
    )
    args = parser.parse_args()
    if not is_live_mode():
        parser.error("Set APP_MODE=live before ingesting into pgvector.")
    try:
        count = ingest_documents(
            WEEK_COLLECTIONS[args.week], markdown_documents(args.week), reset=args.reset
        )
    except LiveRagError as error:
        parser.error(str(error))
    print(f"Ingested {count} document chunk(s) into {WEEK_COLLECTIONS[args.week]}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
