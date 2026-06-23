# Intentionally empty — import ingest_all and search_chunks directly from their
# modules to keep the chromadb import lazy (it happens inside functions, not at
# package load time).
# e.g.:  from app.services.rag.ingestion import ingest_all
#        from app.services.rag.search import search_chunks

__all__ = ["ingest_all", "search_chunks"]
