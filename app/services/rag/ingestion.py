"""
RAG ingestion pipeline.
Pulls visa policy documents from the scraper, chunks them, embeds each chunk
via the external embeddings API (app.services.rag.embeddings), and upserts into
ChromaDB.

Call ingest_all() on startup or via a management command to seed the vector store.
Subsequent calls are idempotent — ChromaDB upsert deduplicates by ID.
"""

import hashlib
import logging
from typing import Optional

from app.services.rag.chroma_client import get_collection
from app.services.rag.chunker import chunk_document
from app.services.rag.embeddings import embed_texts
from app.services.scraper import get_visa_policies

logger = logging.getLogger(__name__)


def ingest_all(
    passport_nationality: Optional[str] = None,
    destination_country: Optional[str] = None,
    travel_purpose: Optional[str] = None,
) -> int:
    """
    Scrape policies → chunk → embed → upsert to ChromaDB.
    Returns the total number of chunks ingested.
    Optional filters allow partial re-ingestion (e.g. a single new policy).
    """
    policies = get_visa_policies(
        passport_nationality, destination_country, travel_purpose
    )
    if not policies:
        logger.warning("No policies returned by scraper — nothing to ingest.")
        return 0

    return ingest_policies(policies)


def ingest_policies(policies: list[dict]) -> int:
    """
    Chunk → embed → upsert a list of already-fetched policy docs to ChromaDB.
    Use this when the caller already has the documents in hand (e.g. the change
    tracker, which diffs the freshly-scraped text and re-ingests the same text
    without fetching it twice). Returns the total number of chunks upserted.
    """
    if not policies:
        return 0

    collection = get_collection()

    total = 0
    for policy in policies:
        chunks = chunk_document(
            content=policy["content"],
            source=policy["source"],
            title=policy["title"],
            passport_nationality=policy["passport_nationality"],
            destination_country=policy["destination_country"],
            travel_purpose=policy["travel_purpose"],
            last_scraped=policy.get("last_scraped"),
        )

        if not chunks:
            continue

        texts = [c["text"] for c in chunks]
        embeddings = embed_texts(texts)
        ids = [
            _chunk_id(policy["source"], policy["title"], c["metadata"]["chunk_index"])
            for c in chunks
        ]
        metadatas = [c["metadata"] for c in chunks]

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        total += len(chunks)
        logger.debug("Ingested %d chunks for: %s", len(chunks), policy["title"])

    logger.info("Ingestion complete: %d total chunks upserted", total)
    return total


def _chunk_id(source: str, title: str, chunk_index: int) -> str:
    """
    Deterministic, collision-resistant ID for a chunk.
    Using a hash keeps IDs short and safe for ChromaDB.
    """
    raw = f"{source}::{title}::{chunk_index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
