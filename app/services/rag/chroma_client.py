"""
ChromaDB initialisation.
Returns a singleton client and the visa_policies collection.
Idempotent: calling get_collection() multiple times returns the same collection.

chromadb is imported lazily (inside functions) so importing this module never
forces the vector-store dependency at app load time.
"""

import logging
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Optional[Any] = None


def get_chroma_client() -> Any:
    global _client
    if _client is None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        _client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info("ChromaDB client initialised at %s", settings.CHROMA_PERSIST_DIR)
    return _client


def get_collection() -> Any:
    """
    Return (or create) the visa_policies collection.
    Uses cosine distance which works well for sentence-transformer embeddings.
    """
    import chromadb  # noqa: PLC0415 — deferred to avoid import at module load

    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return collection
