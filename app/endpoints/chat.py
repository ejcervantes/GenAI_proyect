"""
POST /api/v1/chat — Conversational Q&A endpoint.

Accepts a question + optional visa context (passport, destination, purpose),
runs the Q&A agent, logs the interaction to the DB, and returns the answer
with confidence score, citations, and metadata.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.rag_interaction import RAGInteraction
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, CitationOut
from app.services.llm.agent import ask

logger = logging.getLogger(__name__)
router = APIRouter()


def _confidence_label(score: float) -> str:
    if score >= 0.65:
        return "high"
    if score >= 0.35:
        return "medium"
    return "low"


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ask a visa-related question. Provide passport_nationality,
    destination_country, and travel_purpose for the most accurate results.

    Returns the answer, a confidence score (0–1), source citations,
    and a disclaimer to verify with the embassy.
    """
    # 1. Run the agent
    try:
        response = ask(
            question=payload.question,
            passport_nationality=payload.passport_nationality,
            destination_country=payload.destination_country,
            travel_purpose=payload.travel_purpose,
        )
    except Exception as exc:
        logger.exception("Agent error for user %s: %s", current_user.id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your question. Please try again.",
        )

    # 2. Persist to DB
    sources_json = json.dumps(
        [
            {
                "title": c.title,
                "source": c.source,
                "last_scraped": c.last_scraped,
                "relevance_score": c.relevance_score,
            }
            for c in response.citations
        ]
    )

    interaction = RAGInteraction(
        user_id=current_user.id,
        question=payload.question,
        passport_nationality=payload.passport_nationality,
        destination_country=payload.destination_country,
        travel_purpose=payload.travel_purpose,
        answer=response.answer,
        confidence_score=response.confidence_score,
        sources=sources_json,
        chunks_retrieved=response.chunks_retrieved,
        model_used=response.model_used,
        was_mocked=response.was_mocked,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    # 3. Build response
    return ChatResponse(
        interaction_id=interaction.id,
        question=payload.question,
        answer=response.answer,
        confidence_score=response.confidence_score,
        confidence_label=_confidence_label(response.confidence_score),
        citations=[
            CitationOut(
                title=c.title,
                source=c.source,
                last_scraped=c.last_scraped,
                relevance_score=c.relevance_score,
            )
            for c in response.citations
        ],
        chunks_retrieved=response.chunks_retrieved,
        tools_used=response.tools_used,
        model_used=response.model_used,
        was_mocked=response.was_mocked,
        created_at=interaction.created_at,
    )
