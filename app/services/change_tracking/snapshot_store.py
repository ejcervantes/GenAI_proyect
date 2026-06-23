"""
Policy snapshot store.

Before diffing, we need the *previous* state of a policy.
Snapshots are stored as plain text files under a configurable directory,
keyed by a deterministic hash of (passport_nationality, destination_country, travel_purpose).

Using the filesystem (not the DB) keeps the DB free of large text blobs and
lets the diff logic work on raw strings without ORM round-trips.
"""

import hashlib
import logging
import os
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# Store snapshots next to the ChromaDB data directory
SNAPSHOT_DIR = Path(settings.CHROMA_PERSIST_DIR).parent / "policy_snapshots"


def _snapshot_path(passport_nationality: str, destination_country: str, travel_purpose: str) -> Path:
    key = f"{passport_nationality.lower()}::{destination_country.lower()}::{travel_purpose.lower()}"
    digest = hashlib.sha256(key.encode()).hexdigest()[:16]
    return SNAPSHOT_DIR / f"{digest}.txt"


def load_snapshot(
    passport_nationality: str,
    destination_country: str,
    travel_purpose: str,
) -> str | None:
    """Return the previously saved policy text, or None if no snapshot exists."""
    path = _snapshot_path(passport_nationality, destination_country, travel_purpose)
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Failed to read snapshot %s: %s", path, exc)
        return None


def save_snapshot(
    passport_nationality: str,
    destination_country: str,
    travel_purpose: str,
    text: str,
) -> None:
    """Persist the current policy text as the new snapshot."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = _snapshot_path(passport_nationality, destination_country, travel_purpose)
    try:
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        logger.error("Failed to write snapshot %s: %s", path, exc)
