from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    passport_nationality: Optional[str] = Field(None, max_length=100)
    destination_country: Optional[str] = Field(None, max_length=100)
    travel_purpose: Optional[str] = Field(None, max_length=100)

    model_config = {"json_schema_extra": {
        "example": {
            "question": "What documents do I need for a German student visa?",
            "passport_nationality": "Pakistani",
            "destination_country": "Germany",
            "travel_purpose": "student",
        }
    }}


class CitationOut(BaseModel):
    title: str
    source: str
    last_scraped: str
    relevance_score: float


class ChatResponse(BaseModel):
    interaction_id: int
    question: str
    answer: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    confidence_label: str          # "high" | "medium" | "low"
    citations: list[CitationOut]
    chunks_retrieved: int
    tools_used: list[str]
    model_used: str
    was_mocked: bool
    created_at: datetime

    model_config = {"from_attributes": True}
