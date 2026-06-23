"""
RAG admin endpoints.
POST /api/v1/rag/ingest  — trigger (re-)ingestion of visa policy data
POST /api/v1/rag/search  — test semantic search (debug / dev only)
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional

from app.api.deps.auth import get_current_user
from app.models.user import User

# RAG imports are deferred to inside each route function so that chromadb is
# never imported at module load time, keeping app startup light.

router = APIRouter()


class IngestRequest(BaseModel):
    passport_nationality: Optional[str] = None
    destination_country: Optional[str] = None
    travel_purpose: Optional[str] = None


class IngestResponse(BaseModel):
    chunks_ingested: int
    total_chunks_in_db: int


class SearchRequest(BaseModel):
    query: str
    passport_nationality: Optional[str] = None
    destination_country: Optional[str] = None
    travel_purpose: Optional[str] = None
    top_k: int = 5


class ChunkResult(BaseModel):
    id: str
    text: str
    relevance_score: float
    source: str
    title: str
    last_scraped: str


class SearchResponse(BaseModel):
    query: str
    results: list[ChunkResult]


@router.post("/ingest", response_model=IngestResponse)
def trigger_ingest(
    payload: IngestRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Trigger (re-)ingestion of visa policy data into ChromaDB.
    Pass filters to re-ingest a specific subset; leave empty to ingest all.
    Requires authentication.
    """
    from app.services.rag.ingestion import ingest_all
    from app.services.rag.chroma_client import get_collection

    n = ingest_all(
        passport_nationality=payload.passport_nationality,
        destination_country=payload.destination_country,
        travel_purpose=payload.travel_purpose,
    )
    total = get_collection().count()
    return IngestResponse(chunks_ingested=n, total_chunks_in_db=total)


@router.post("/search", response_model=SearchResponse)
def test_search(
    payload: SearchRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Test semantic search over ChromaDB.
    Returns raw chunk results with relevance scores.
    Useful for debugging retrieval quality. Requires authentication.
    """
    from app.services.rag.search import search_chunks

    chunks = search_chunks(
        query=payload.query,
        passport_nationality=payload.passport_nationality,
        destination_country=payload.destination_country,
        travel_purpose=payload.travel_purpose,
        top_k=payload.top_k,
    )

    results = [
        ChunkResult(
            id=c["id"],
            text=c["text"],
            relevance_score=c["relevance_score"],
            source=c["metadata"].get("source", ""),
            title=c["metadata"].get("title", ""),
            last_scraped=c["metadata"].get("last_scraped", ""),
        )
        for c in chunks
    ]

    return SearchResponse(query=payload.query, results=results)
