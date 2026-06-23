"""
Semantic search over the ChromaDB visa_policies collection.

search_chunks() is the main entry point used by the Q&A agent (Step 4),
the checklist generator (Step 5), and the change tracker (Step 6).
"""

import logging
from typing import Optional

# chromadb is imported lazily inside search_chunks so importing this module never
# pulls in the vector-store dependency at app load time. Query embedding goes
# through the external API client (app.services.rag.embeddings), which is light.

logger = logging.getLogger(__name__)


def search_chunks(
    query: str,
    passport_nationality: Optional[str] = None,
    destination_country: Optional[str] = None,
    travel_purpose: Optional[str] = None,
    top_k: int = 5,
) -> list[dict]:
    """
    Embed *query* and return the top_k most semantically similar chunks
    that match the optional metadata filters.

    Each returned dict has keys:
      - id: chunk id
      - text: the chunk content
      - metadata: dict with source, title, passport_nationality,
                  destination_country, travel_purpose, last_scraped
      - distance: cosine distance (lower = more similar, range 0–2)
      - relevance_score: 1 - distance/2  (range 0–1, higher = better)
    """
    from app.services.rag.chroma_client import get_collection
    from app.services.rag.embeddings import embed_query

    try:
        collection = get_collection()
    except Exception as exc:
        logger.error("Could not open ChromaDB collection: %s", exc)
        return []

    if collection.count() == 0:
        logger.warning("ChromaDB collection is empty. Run ingestion first.")
        return []

    try:
        query_embedding = embed_query(query)
    except RuntimeError as exc:
        logger.error("Query embedding failed: %s", exc)
        return []

    # Build ChromaDB metadata filter
    where_clause = _build_where(
        passport_nationality, destination_country, travel_purpose
    )

    query_kwargs: dict = {
        "query_embeddings": [query_embedding],
        "n_results": min(top_k, collection.count()),
        "include": ["documents", "metadatas", "distances"],
    }
    if where_clause:
        query_kwargs["where"] = where_clause

    try:
        results = collection.query(**query_kwargs)
    except Exception as exc:
        logger.error("ChromaDB query failed: %s", exc)
        return []

    return _format_results(results)


def _build_where(
    passport_nationality: Optional[str],
    destination_country: Optional[str],
    travel_purpose: Optional[str],
) -> Optional[dict]:
    """
    Construct a ChromaDB $and filter, but ONLY for values the caller actually
    specified. Empty values and the sentinel "general" mean "no preference" and
    add no filter — otherwise an unspecified query would hard-exclude every
    nationality/purpose-tagged document and retrieval would return nothing.

    When a real value is given we still $or it with "general"-tagged docs so
    cross-cutting content (e.g. post-arrival registration) is always eligible.
    """

    def _meaningful(value: Optional[str]) -> Optional[str]:
        v = (value or "").strip().lower()
        return v if v and v != "general" else None

    conditions = []

    passport = _meaningful(passport_nationality)
    if passport:
        conditions.append(
            {
                "$or": [
                    {"passport_nationality": {"$eq": passport}},
                    {"passport_nationality": {"$eq": "general"}},
                ]
            }
        )

    destination = _meaningful(destination_country)
    if destination:
        conditions.append({"destination_country": {"$eq": destination}})

    purpose = _meaningful(travel_purpose)
    if purpose:
        conditions.append(
            {
                "$or": [
                    {"travel_purpose": {"$eq": purpose}},
                    {"travel_purpose": {"$eq": "general"}},
                ]
            }
        )

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def _format_results(raw: dict) -> list[dict]:
    """
    Flatten ChromaDB query results into a clean list of dicts.
    """
    ids = raw.get("ids", [[]])[0]
    docs = raw.get("documents", [[]])[0]
    metas = raw.get("metadatas", [[]])[0]
    dists = raw.get("distances", [[]])[0]

    formatted = []
    for chunk_id, text, meta, dist in zip(ids, docs, metas, dists):
        formatted.append(
            {
                "id": chunk_id,
                "text": text,
                "metadata": meta,
                "distance": dist,
                "relevance_score": round(max(0.0, 1.0 - dist / 2.0), 4),
            }
        )

    # Sort by relevance descending (ChromaDB already returns sorted but let's be explicit)
    formatted.sort(key=lambda x: x["relevance_score"], reverse=True)
    return formatted
