from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class DocumentOut(BaseModel):
    id: int
    filename: str
    file_type: str
    mime_type: Optional[str]
    extraction_status: str
    extraction_confidence: Optional[float]
    fill_status: Optional[str]
    filled_form_path: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ScannedFieldsOut(BaseModel):
    """Full scan result including extracted field values and confidence scores."""
    id: int
    filename: str
    file_type: str
    extraction_status: str
    extraction_confidence: Optional[float]
    fields: dict[str, Any]             # extracted field values
    field_confidence: dict[str, float] # per-field confidence 0–1
    flagged_fields: list[str]          # fields below threshold
    low_confidence_threshold: float
    created_at: datetime

    model_config = {"from_attributes": True}


class FormFillRequest(BaseModel):
    """
    POST /api/v1/documents/{doc_id}/fill
    Supply personal data to fill into the form.
    If omitted, the service looks for a previously scanned passport
    belonging to the same user and uses its extracted fields.
    """
    personal_data: Optional[dict[str, Any]] = None


class FilledFormOut(BaseModel):
    id: int
    filename: str
    fill_status: Optional[str]
    filled_form_path: Optional[str]
    filled_fields: dict[str, str]
    unfilled_fields: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}
