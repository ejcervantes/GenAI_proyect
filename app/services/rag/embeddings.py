"""
Embeddings for the RAG pipeline — external API with a deterministic fallback.

The default provider is OpenAI (``text-embedding-3-small``), selected via
``settings.EMBEDDING_PROVIDER``. Switching providers later only requires adding
a branch here and updating the config — nothing else in the pipeline imports a
specific embedding backend.

When no API key is configured (``settings.embeddings_use_mock``), a deterministic
hash-based fallback is used. Those vectors are NOT semantically meaningful, but
they keep ingestion and search fully functional during development so the app
never crashes for lack of a key. Set ``OPENAI_API_KEY`` for real retrieval.

IMPORTANT: ingestion and querying must use the *same* backend within a run —
vectors produced by the mock and by the real API are not comparable. Both paths
read ``settings.embeddings_use_mock`` so they stay consistent automatically.
"""

import hashlib
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# OpenAI caps a single embeddings request at 2048 inputs; stay well under it.
_MAX_BATCH = 256


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of texts, returning one vector per input in the same order.
    Empty input returns an empty list.
    """
    if not texts:
        return []

    if settings.embeddings_use_mock:
        if settings.EMBEDDING_PROVIDER != "mock":
            logger.warning(
                "No OPENAI_API_KEY configured — using non-semantic mock embeddings. "
                "Retrieval quality will be poor; set a real key for production."
            )
        return [_mock_embed(t) for t in texts]

    if settings.EMBEDDING_PROVIDER == "openai":
        return _openai_embed(texts)

    raise RuntimeError(
        f"Unknown EMBEDDING_PROVIDER '{settings.EMBEDDING_PROVIDER}'. "
        "Supported: 'openai', 'mock'."
    )


def embed_query(text: str) -> list[float]:
    """Embed a single query string and return its vector."""
    return embed_texts([text])[0]


# ── OpenAI provider ──────────────────────────────────────────────────────────


def _openai_embed(texts: list[str]) -> list[list[float]]:
    """
    Call the OpenAI embeddings endpoint in batches and return vectors in order.
    Raises RuntimeError on any HTTP/transport failure so callers can degrade.
    """
    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
    vectors: list[list[float]] = []

    with httpx.Client(timeout=60.0) as client:
        for start in range(0, len(texts), _MAX_BATCH):
            batch = texts[start : start + _MAX_BATCH]
            payload = {"model": settings.EMBEDDING_MODEL, "input": batch}
            try:
                resp = client.post(
                    f"{settings.OPENAI_BASE_URL}/embeddings",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(
                    f"OpenAI embeddings returned HTTP {exc.response.status_code}: "
                    f"{exc.response.text}"
                ) from exc
            except httpx.HTTPError as exc:
                raise RuntimeError(f"OpenAI embeddings request failed: {exc}") from exc

            data = sorted(resp.json()["data"], key=lambda d: d["index"])
            vectors.extend(item["embedding"] for item in data)

    return vectors


# ── Deterministic fallback ───────────────────────────────────────────────────


def _mock_embed(text: str) -> list[float]:
    """
    Deterministic bag-of-tokens vector hashed into EMBEDDING_DIMENSIONS buckets,
    then L2-normalised. Not semantically meaningful — only good enough to keep
    the pipeline runnable and to give weakly-discriminative similarity in dev.
    """
    dims = settings.EMBEDDING_DIMENSIONS
    vec = [0.0] * dims

    for token in text.lower().split():
        bucket = int(hashlib.sha256(token.encode()).hexdigest(), 16) % dims
        vec[bucket] += 1.0

    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]
