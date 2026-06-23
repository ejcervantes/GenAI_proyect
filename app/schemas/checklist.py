from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Visa Case schemas ──────────────────────────────────────────────────────────


class VisaCaseCreate(BaseModel):
    passport_nationality: str = Field(..., max_length=100)
    destination_country: str = Field(..., max_length=100)
    travel_purpose: str = Field(..., max_length=100)
    visa_category: Optional[str] = Field(None, max_length=100)
    travel_date: Optional[datetime] = None
    residence_country: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None

    model_config = {"json_schema_extra": {
        "example": {
            "passport_nationality": "Pakistani",
            "destination_country": "Germany",
            "travel_purpose": "student",
        }
    }}


class VisaCaseOut(BaseModel):
    id: int
    passport_nationality: str
    destination_country: str
    travel_purpose: str
    visa_category: Optional[str]
    travel_date: Optional[datetime]
    residence_country: Optional[str]
    notes: Optional[str]
    is_tracking: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Checklist item schemas ─────────────────────────────────────────────────────


class ChecklistItemOut(BaseModel):
    id: int
    order: int
    document_name: str
    description: Optional[str]
    is_mandatory: bool
    is_conditional: bool
    condition_note: Optional[str]
    requires_translation: bool
    requires_notarization: bool
    is_completed: bool
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ChecklistItemUpdate(BaseModel):
    is_completed: bool


# ── Checklist schemas ──────────────────────────────────────────────────────────


class ChecklistOut(BaseModel):
    id: int
    visa_case_id: int
    title: str
    confidence_score: Optional[float]
    sources: Optional[str]   # raw JSON string; frontend can parse if needed
    created_at: datetime
    items: list[ChecklistItemOut]

    model_config = {"from_attributes": True}


class ChecklistGenerateRequest(BaseModel):
    """
    POST /api/v1/checklists
    Either supply a visa_case_id (existing case) or an inline case triple.
    At least one must be provided.
    """
    visa_case_id: Optional[int] = None

    # Inline triple — used when the user doesn't have a saved VisaCase yet
    passport_nationality: Optional[str] = Field(None, max_length=100)
    destination_country: Optional[str] = Field(None, max_length=100)
    travel_purpose: Optional[str] = Field(None, max_length=100)

    model_config = {"json_schema_extra": {
        "examples": [
            {"visa_case_id": 1},
            {
                "passport_nationality": "Indian",
                "destination_country": "United Kingdom",
                "travel_purpose": "student",
            },
        ]
    }}
