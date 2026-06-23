"""
Document chunking for the RAG pipeline.
Splits raw policy text into overlapping chunks so that semantically
complete sentences are never cut off across a chunk boundary.
"""

import re
from typing import Optional


# Chunk size targets in characters (kept dependency-free — no tokenizer needed).
# ~1600 chars ≈ 350–450 tokens for English prose, matching the 300–500 token
# target in the project spec. Overlap preserves context across boundaries.
CHUNK_SIZE = 1600
CHUNK_OVERLAP = 200


def chunk_document(
    content: str,
    source: str,
    title: str,
    passport_nationality: str,
    destination_country: str,
    travel_purpose: str,
    last_scraped: Optional[str] = None,
) -> list[dict]:
    """
    Split *content* into overlapping chunks and attach metadata to each.
    Returns a list of dicts with keys: text, metadata.
    """
    sentences = _split_sentences(content)
    chunks = _group_into_chunks(sentences)

    result = []
    for i, chunk_text in enumerate(chunks):
        result.append(
            {
                "text": chunk_text.strip(),
                "metadata": {
                    "source": source,
                    "title": title,
                    "passport_nationality": passport_nationality.lower(),
                    "destination_country": destination_country.lower(),
                    "travel_purpose": travel_purpose.lower(),
                    "last_scraped": last_scraped or "",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            }
        )
    return result


def _split_sentences(text: str) -> list[str]:
    """
    Naive sentence splitter: split on '. ', '! ', '? ', and newlines.
    Good enough for structured policy text.
    """
    parts = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    return [p.strip() for p in parts if p.strip()]


def _group_into_chunks(sentences: list[str]) -> list[str]:
    """
    Greedily group sentences into chunks up to CHUNK_SIZE chars.
    Overlap is achieved by re-adding the last sentence(s) of the previous chunk.
    """
    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence) + 1  # +1 for the space separator
        if current_len + sentence_len > CHUNK_SIZE and current:
            chunks.append(" ".join(current))
            # Carry over overlap: last sentence(s) totalling ~CHUNK_OVERLAP chars
            overlap: list[str] = []
            overlap_len = 0
            for s in reversed(current):
                if overlap_len + len(s) > CHUNK_OVERLAP:
                    break
                overlap.insert(0, s)
                overlap_len += len(s) + 1
            current = overlap
            current_len = overlap_len

        current.append(sentence)
        current_len += sentence_len

    if current:
        chunks.append(" ".join(current))

    return chunks
