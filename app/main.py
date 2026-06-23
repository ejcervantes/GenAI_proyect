from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.endpoints.router import router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify DB connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connected")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

    # Startup: seed the RAG vector store from the curated source corpus.
    # Embeddings go through the external API with a deterministic fallback, so
    # this runs whether or not OPENAI_API_KEY is set (retrieval quality differs,
    # not the control flow). Failures here are non-fatal — the API still serves.
    if settings.embeddings_use_mock:
        print(
            "ℹ️  No OPENAI_API_KEY set — RAG will use non-semantic mock embeddings "
            "(dev only; set a key for real retrieval)."
        )
    try:
        from app.services.rag.chroma_client import get_collection
        from app.services.rag.ingestion import ingest_all

        collection = get_collection()
        if collection.count() == 0:
            print("🔄 Vector store empty — running initial ingestion...")
            n = ingest_all()
            print(f"✅ RAG ingestion complete: {n} chunks indexed")
        else:
            print(f"✅ Vector store ready ({collection.count()} chunks indexed)")
    except Exception as e:
        print(f"⚠️  RAG initialisation failed (non-fatal): {e}")

    # Startup: launch APScheduler for periodic change tracking
    try:
        from app.tasks.scheduler import start_scheduler

        start_scheduler()
        print(
            f"✅ Change-tracking scheduler started (interval: {settings.POLICY_REFRESH_INTERVAL_HOURS}h)"
        )
    except Exception as e:
        print(f"⚠️  Scheduler failed to start (non-fatal): {e}")

    yield

    # Shutdown: stop the background scheduler cleanly
    try:
        from app.tasks.scheduler import stop_scheduler

        stop_scheduler()
    except Exception:
        pass


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Domain-specific visa workflow assistant",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
