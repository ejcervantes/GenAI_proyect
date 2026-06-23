"""
Change alerts endpoints.

GET    /api/v1/change-alerts              — list alerts for current user (filterable)
GET    /api/v1/change-alerts/{id}         — get a specific alert
PATCH  /api/v1/change-alerts/{id}/read    — mark alert as read/unread
POST   /api/v1/change-alerts/run          — re-check the current user's cases now
POST   /api/v1/change-alerts/refresh-global — run the global RAG refresh now (all sources)
GET    /api/v1/change-alerts/visa-cases/{case_id} — alerts for one specific visa case
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.change_alert import ChangeAlert
from app.models.user import User
from app.models.visa_case import VisaCase
from app.schemas.change_alert import (
    ChangeAlertOut,
    GlobalRefreshResponse,
    ManualCheckResponse,
    MarkReadRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _user_case_ids(user_id: int, db: Session) -> list[int]:
    return [
        row.id
        for row in db.query(VisaCase.id).filter(VisaCase.user_id == user_id).all()
    ]


def _get_alert_or_404(alert_id: int, user_id: int, db: Session) -> ChangeAlert:
    case_ids = _user_case_ids(user_id, db)
    alert = (
        db.query(ChangeAlert)
        .filter(ChangeAlert.id == alert_id, ChangeAlert.visa_case_id.in_(case_ids))
        .first()
    )
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


@router.get("", response_model=list[ChangeAlertOut])
def list_change_alerts(
    unread_only: bool = Query(False, description="Return only unread alerts"),
    severity: str | None = Query(None, description="Filter by severity: info | warning | critical"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all change alerts for the current user's visa cases.
    Optionally filter by read status or severity.
    """
    case_ids = _user_case_ids(current_user.id, db)
    if not case_ids:
        return []

    q = (
        db.query(ChangeAlert)
        .filter(ChangeAlert.visa_case_id.in_(case_ids))
    )
    if unread_only:
        q = q.filter(ChangeAlert.is_read == False)  # noqa: E712
    if severity:
        q = q.filter(ChangeAlert.severity == severity)

    return q.order_by(ChangeAlert.detected_at.desc()).all()


@router.get("/visa-cases/{case_id}", response_model=list[ChangeAlertOut])
def list_alerts_for_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all change alerts for a specific visa case."""
    # Verify ownership
    case = (
        db.query(VisaCase)
        .filter(VisaCase.id == case_id, VisaCase.user_id == current_user.id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visa case not found")

    return (
        db.query(ChangeAlert)
        .filter(ChangeAlert.visa_case_id == case_id)
        .order_by(ChangeAlert.detected_at.desc())
        .all()
    )


@router.get("/{alert_id}", response_model=ChangeAlertOut)
def get_change_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific change alert."""
    return _get_alert_or_404(alert_id, current_user.id, db)


@router.patch("/{alert_id}/read", response_model=ChangeAlertOut)
def mark_alert_read(
    alert_id: int,
    payload: MarkReadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an alert as read or unread."""
    alert = _get_alert_or_404(alert_id, current_user.id, db)
    alert.is_read = payload.is_read
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/run", response_model=ManualCheckResponse)
def run_tracking_now(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually trigger the change-tracking job immediately.
    Useful for testing or forcing a refresh without waiting for the scheduler.
    Checks only the current user's tracked visa cases.
    """
    # Scope the job to just this user's cases for the manual trigger
    cases = (
        db.query(VisaCase)
        .filter(
            VisaCase.user_id == current_user.id,
            VisaCase.is_tracking == True,  # noqa: E712
        )
        .all()
    )

    from app.services.change_tracking.tracker import check_case

    changed = 0
    errors = 0
    for case in cases:
        try:
            if check_case(case, db):
                changed += 1
        except Exception as exc:
            logger.error("Manual check error for case #%d: %s", case.id, exc)
            errors += 1

    return ManualCheckResponse(
        cases_checked=len(cases),
        changes_found=changed,
        errors=errors,
    )


@router.post("/refresh-global", response_model=GlobalRefreshResponse)
def refresh_global_now(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually run the global RAG refresh immediately (the same job the scheduler
    runs daily): re-scrape every source, re-ingest what changed, and raise alerts
    for all tracked cases matching a changed source. Handy for testing without
    waiting for the daily tick.
    """
    from app.services.change_tracking.tracker import run_global_refresh_job

    result = run_global_refresh_job(db)
    return GlobalRefreshResponse(**result)
