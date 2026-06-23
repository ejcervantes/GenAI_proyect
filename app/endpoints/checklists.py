"""
Checklist + VisaCase endpoints.

POST   /api/v1/checklists              — generate a new checklist
GET    /api/v1/checklists              — list all checklists for current user
GET    /api/v1/checklists/{id}         — get a specific checklist with items
PATCH  /api/v1/checklists/{checklist_id}/items/{item_id}  — mark item complete/incomplete

POST   /api/v1/visa-cases             — create a visa case
GET    /api/v1/visa-cases             — list visa cases for current user
GET    /api/v1/visa-cases/{id}        — get a specific visa case
DELETE /api/v1/visa-cases/{id}        — delete a visa case
"""

import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session, selectinload

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.checklist import Checklist, ChecklistItem
from app.models.user import User
from app.models.visa_case import VisaCase
from app.schemas.checklist import (
    ChecklistGenerateRequest,
    ChecklistItemUpdate,
    ChecklistOut,
    VisaCaseCreate,
    VisaCaseOut,
)
from app.services.checklist_export import render_pdf, render_text
from app.services.checklist_service import generate_checklist

logger = logging.getLogger(__name__)

# Two routers from one module:
#   router            → mounted at /checklists
#   visa_cases_router → mounted at /visa-cases   (what the frontend calls)
# They were previously merged under /checklists, so the frontend's
# /api/v1/visa-cases calls 404'd. Keeping them separate fixes that.
router = APIRouter()
visa_cases_router = APIRouter()


# ══════════════════════════════════════════════════════════════════════════════
# Visa Cases
# ══════════════════════════════════════════════════════════════════════════════


@visa_cases_router.post("", response_model=VisaCaseOut, status_code=status.HTTP_201_CREATED)
def create_visa_case(
    payload: VisaCaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new visa case (passport / destination / purpose triple)."""
    case = VisaCase(
        user_id=current_user.id,
        passport_nationality=payload.passport_nationality,
        destination_country=payload.destination_country,
        travel_purpose=payload.travel_purpose,
        visa_category=payload.visa_category,
        travel_date=payload.travel_date,
        residence_country=payload.residence_country,
        notes=payload.notes,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@visa_cases_router.get("", response_model=list[VisaCaseOut])
def list_visa_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all visa cases belonging to the current user."""
    return (
        db.query(VisaCase)
        .filter(VisaCase.user_id == current_user.id)
        .order_by(VisaCase.created_at.desc())
        .all()
    )


@visa_cases_router.get("/{case_id}", response_model=VisaCaseOut)
def get_visa_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific visa case."""
    case = _get_case_or_404(case_id, current_user.id, db)
    return case


@visa_cases_router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visa_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a visa case and all associated checklists and alerts."""
    case = _get_case_or_404(case_id, current_user.id, db)
    db.delete(case)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# Checklists
# ══════════════════════════════════════════════════════════════════════════════


@router.post("", response_model=ChecklistOut, status_code=status.HTTP_201_CREATED)
def create_checklist(
    payload: ChecklistGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a personalised document checklist.

    Supply either `visa_case_id` (uses a saved case) or the inline triple
    (`passport_nationality`, `destination_country`, `travel_purpose`).
    When the inline triple is used, a VisaCase is created automatically.
    """
    # Resolve or create the VisaCase
    if payload.visa_case_id:
        visa_case = _get_case_or_404(payload.visa_case_id, current_user.id, db)
    elif payload.passport_nationality and payload.destination_country and payload.travel_purpose:
        visa_case = VisaCase(
            user_id=current_user.id,
            passport_nationality=payload.passport_nationality,
            destination_country=payload.destination_country,
            travel_purpose=payload.travel_purpose,
        )
        db.add(visa_case)
        db.flush()
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Provide either visa_case_id or all three of: "
                "passport_nationality, destination_country, travel_purpose."
            ),
        )

    # Generate and persist the checklist
    try:
        checklist = generate_checklist(visa_case=visa_case, db=db)
    except Exception as exc:
        logger.exception("Checklist generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Checklist generation failed. Please try again.",
        )

    # Reload with items for the response
    return _load_checklist(checklist.id, db)


@router.get("", response_model=list[ChecklistOut])
def list_checklists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all checklists for the current user (with items)."""
    case_ids = [
        c.id
        for c in db.query(VisaCase.id).filter(VisaCase.user_id == current_user.id).all()
    ]
    if not case_ids:
        return []

    return (
        db.query(Checklist)
        .options(selectinload(Checklist.items))
        .filter(Checklist.visa_case_id.in_(case_ids))
        .order_by(Checklist.created_at.desc())
        .all()
    )


@router.get("/{checklist_id}", response_model=ChecklistOut)
def get_checklist(
    checklist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific checklist with all items."""
    checklist = _load_checklist(checklist_id, db)
    _assert_checklist_owner(checklist, current_user.id, db)
    return checklist


@router.get("/{checklist_id}/export")
def export_checklist(
    checklist_id: int,
    format: str = Query("pdf", pattern="^(pdf|txt)$", description="pdf | txt"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export a checklist as a downloadable PDF or plain-text file.
    Use ?format=pdf (default) or ?format=txt.
    """
    checklist = _load_checklist(checklist_id, db)
    _assert_checklist_owner(checklist, current_user.id, db)

    filename = _safe_filename(checklist.title or "checklist")

    if format == "txt":
        body = render_text(checklist).encode("utf-8")
        return Response(
            content=body,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.txt"'
            },
        )

    try:
        pdf_bytes = render_pdf(checklist)
    except Exception as exc:
        logger.exception("Checklist PDF export failed for #%d: %s", checklist_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate the PDF. Try the plain-text export (?format=txt).",
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
    )


@router.patch(
    "/{checklist_id}/items/{item_id}",
    response_model=ChecklistOut,
)
def update_checklist_item(
    checklist_id: int,
    item_id: int,
    payload: ChecklistItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a checklist item as completed or not completed.
    Returns the full updated checklist.
    """
    checklist = _load_checklist(checklist_id, db)
    _assert_checklist_owner(checklist, current_user.id, db)

    item = db.query(ChecklistItem).filter(
        ChecklistItem.id == item_id,
        ChecklistItem.checklist_id == checklist_id,
    ).first()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    item.is_completed = payload.is_completed
    item.completed_at = datetime.now(timezone.utc) if payload.is_completed else None
    db.commit()

    return _load_checklist(checklist_id, db)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _get_case_or_404(case_id: int, user_id: int, db: Session) -> VisaCase:
    case = (
        db.query(VisaCase)
        .filter(VisaCase.id == case_id, VisaCase.user_id == user_id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visa case not found")
    return case


def _load_checklist(checklist_id: int, db: Session) -> Checklist:
    checklist = (
        db.query(Checklist)
        .options(selectinload(Checklist.items))
        .filter(Checklist.id == checklist_id)
        .first()
    )
    if not checklist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found")
    return checklist


def _assert_checklist_owner(checklist: Checklist, user_id: int, db: Session) -> None:
    case = db.query(VisaCase).filter(
        VisaCase.id == checklist.visa_case_id,
        VisaCase.user_id == user_id,
    ).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _safe_filename(title: str) -> str:
    """Slugify a checklist title into a safe download filename (no extension)."""
    slug = re.sub(r"[^\w\-]+", "_", title.strip()).strip("_").lower()
    return slug[:80] or "checklist"
