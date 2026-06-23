from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All application settings are loaded from the .env file.
    Required fields (no defaults) must be set in .env or as environment variables.
    Fields with defaults will work out of the box for local development.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # -------------------------------------------------------------------------
    # App
    # -------------------------------------------------------------------------
    APP_NAME: str = "PassportAI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # -------------------------------------------------------------------------
    # Database — set DATABASE_URL in .env
    # Format: postgresql://user:password@host:port/dbname
    # -------------------------------------------------------------------------
    DATABASE_URL: str = "postgresql://passportai:passportai@localhost:5432/passportai"

    # -------------------------------------------------------------------------
    # Auth — change SECRET_KEY in production, never commit the real value
    # -------------------------------------------------------------------------
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # -------------------------------------------------------------------------
    # Redis — used for background task queuing and cron jobs
    # -------------------------------------------------------------------------
    REDIS_URL: str = "redis://redis:6379/0"

    # -------------------------------------------------------------------------
    # LLM — text generation for the Q&A agent, checklist extractor and change
    # summariser. Provider is pluggable via LLM_PROVIDER:
    #   "openai" → OpenAI Chat Completions (uses OPENAI_API_KEY / OPENAI_BASE_URL
    #              from the Embeddings section below; model = OPENAI_CHAT_MODEL)
    #   "ollama" → local Ollama server (OLLAMA_BASE_URL / OLLAMA_MODEL)
    #   "mock"   → deterministic stub, no network (CI / offline dev)
    # -------------------------------------------------------------------------
    LLM_PROVIDER: str = "openai"
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"

    # Ollama (only used when LLM_PROVIDER="ollama")
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_VISION_MODEL: str = "llava"

    # Document scanner (vision). Kept independent from the text LLM so switching
    # the chat model to OpenAI does not require a vision model to be available.
    # Set VISION_MOCK=false only when a real vision backend is wired up.
    VISION_MOCK: bool = True

    # -------------------------------------------------------------------------
    # Embeddings — external API used to vectorise RAG chunks and queries.
    # Provider is pluggable; default is OpenAI text-embedding-3-small.
    # When OPENAI_API_KEY is empty (or EMBEDDING_PROVIDER="mock"), a deterministic
    # local fallback is used so the pipeline still runs end-to-end without a key.
    # The fallback vectors are NOT semantically meaningful — set a real key for
    # production-quality retrieval.
    # -------------------------------------------------------------------------
    EMBEDDING_PROVIDER: str = "openai"          # openai | mock
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536            # must match the chosen model
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # -------------------------------------------------------------------------
    # ChromaDB — local vector database for the RAG pipeline.
    # Stores embedded visa policy chunks for semantic search. Embeddings are
    # supplied explicitly (via the external API above), so Chroma's own default
    # embedding function is never used.
    # -------------------------------------------------------------------------
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    CHROMA_COLLECTION_NAME: str = "visa_policies"

    # -------------------------------------------------------------------------
    # Scraper — fetches visa policy data from official PK→DE sources.
    # SCRAPER_MOCK=true forces the curated seed corpus only (no live fetches).
    # SCRAPER_MOCK=false attempts live scraping and falls back to the seed
    # content per-source when a fetch fails or returns thin content.
    # -------------------------------------------------------------------------
    SCRAPER_MOCK: bool = True

    # -------------------------------------------------------------------------
    # Change tracking — how often the scheduler re-scrapes sources and, when the
    # text differs from the previous snapshot, re-ingests the RAG. Daily = 24h.
    # -------------------------------------------------------------------------
    POLICY_REFRESH_INTERVAL_HOURS: int = 24

    @property
    def embeddings_use_mock(self) -> bool:
        """True when no real embedding provider/key is configured."""
        return self.EMBEDDING_PROVIDER == "mock" or not self.OPENAI_API_KEY


settings = Settings()
