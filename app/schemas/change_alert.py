from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ChangeAlertOut(BaseModel):
    id: int
    visa_case_id: int
    source_url: Optional[str]
    change_type: str
    summary: str
    raw_diff: Optional[str]
    action_required: Optional[str]
    severity: str          # info | warning | critical
    is_read: bool
    detected_at: datetime

    model_config = {"from_attributes": True}


class MarkReadRequest(BaseModel):
    is_read: bool = True


class ManualCheckResponse(BaseModel):
    """Response from POST /change-alerts/run — manual trigger of the tracking job."""
    cases_checked: int
    changes_found: int
    errors: int


class GlobalRefreshResponse(BaseModel):
    """Response from POST /change-alerts/refresh-global — manual global refresh."""
    triples_checked: int
    triples_changed: int
    alerts_created: int
    errors: int
