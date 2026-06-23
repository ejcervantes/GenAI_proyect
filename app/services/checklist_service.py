"""
Checklist generator service.

generate_checklist() is the main entry point called by the endpoint.
It:
  1. Calls get_document_checklist tool to retrieve relevant RAG chunks
  2. Passes chunks to the LLM extractor to get structured items
  3. Persists a Checklist + ChecklistItems to the DB
  4. Returns the saved Checklist ORM object (with items loaded)
"""

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.checklist import Checklist, ChecklistItem
from app.models.visa_case import VisaCase
from app.services.llm.checklist_extractor import extract_checklist_items
from app.services.rag.search import search_chunks

logger = logging.getLogger(__name__)

TOP_K = 6  # chunks to pull for checklist generation


# ── Tool function (mirrors pattern from tools.py) ──────────────────────────────


def get_document_checklist_context(
    passport_nationality: str,
    destination_country: str,
    travel_purpose: str,
) -> tuple[str, list[dict], float]:
    """
    Retrieve the most relevant chunks for building a document checklist.
    Returns (context_text, raw_chunks, avg_relevance).
    """
    query = (
        f"required documents checklist {passport_nationality} visa {destination_country} "
        f"{travel_purpose} application documents needed list"
    )

    chunks = search_chunks(
        query=query,
        passport_nationality=passport_nationality,
        destination_country=destination_country,
        travel_purpose=travel_purpose,
        top_k=TOP_K,
    )

    if not chunks:
        return ("No visa policy documents found for this combination.", [], 0.0)

    context_parts = [f"[{i+1}] {c['text']}" for i, c in enumerate(chunks)]
    context_text = "\n\n".join(context_parts)
    avg_rel = round(sum(c["relevance_score"] for c in chunks) / len(chunks), 4)

    return context_text, chunks, avg_rel


# ── Main service function ──────────────────────────────────────────────────────


def generate_checklist(
    visa_case: VisaCase,
    db: Session,
) -> Checklist:
    """
    Generate a personalized document checklist for the given VisaCase and
    persist it to the database. Returns the newly created Checklist with items.
    """
    nationality = visa_case.passport_nationality
    destination = visa_case.destination_country
    purpose = visa_case.travel_purpose

    # 1. Retrieve relevant chunks
    context_text, raw_chunks, avg_relevance = get_document_checklist_context(
        passport_nationality=nationality,
        destination_country=destination,
        travel_purpose=purpose,
    )

    # 2. Extract structured items via LLM
    items_data = extract_checklist_items(
        context=context_text,
        passport_nationality=nationality,
        destination_country=destination,
        travel_purpose=purpose,
    )

    # 3. Build source citations JSON
    sources = list({c["metadata"].get("source", "") for c in raw_chunks if c["metadata"].get("source")})
    sources_json = json.dumps(sources)

    # 4. Checklist title
    title = (
        f"{nationality} → {destination} ({purpose.capitalize()}) — Document Checklist"
    )

    # 5. Persist Checklist header
    checklist = Checklist(
        visa_case_id=visa_case.id,
        title=title,
        confidence_score=avg_relevance,
        sources=sources_json,
    )
    db.add(checklist)
    db.flush()  # get checklist.id without committing yet

    # 6. Persist ChecklistItems
    for item_data in items_data:
        item = ChecklistItem(
            checklist_id=checklist.id,
            order=item_data.order,
            document_name=item_data.document_name,
            description=item_data.description,
            is_mandatory=item_data.is_mandatory,
            is_conditional=item_data.is_conditional,
            condition_note=item_data.condition_note,
            requires_translation=item_data.requires_translation,
            requires_notarization=item_data.requires_notarization,
            is_completed=False,
        )
        db.add(item)

    db.commit()
    db.refresh(checklist)

    logger.info(
        "Checklist #%d generated for case #%d: %d items (confidence=%.2f)",
        checklist.id,
        visa_case.id,
        len(items_data),
        avg_relevance,
    )

    return checklist
