"""
Documents endpoints — Step 7 (scanner) + Step 8 (form filler).

POST /api/v1/documents/scan
    Upload a passport or national ID image/PDF.
    Returns extracted fields with per-field confidence scores.
    Low-confidence fields are flagged for user review.

POST /api/v1/documents/{doc_id}/fill
    Upload a blank visa form (PDF or DOCX).
    Personal data is sourced from the request body or auto-loaded from the
    user's most recent passport scan. Returns the filled form for download.

GET  /api/v1/documents
    List all documents for the current user.

GET  /api/v1/documents/{doc_id}
    Get a specific document with extracted fields.

GET  /api/v1/documents/{doc_id}/download
    Download the filled form file.
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentOut, FilledFormOut, FormFillRequest, ScannedFieldsOut
from app.services.form_filler_service import fill_form
from app.services.scanner_service import scan_document

logger = logging.getLogger(__name__)
router = APIRouter()

# Accepted MIME types for scanner
_SCAN_ALLOWED = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
# Accepted MIME types for form filler
_FORM_ALLOWED = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


# ══════════════════════════════════════════════════════════════════════════════
# Scanner — Step 7
# ══════════════════════════════════════════════════════════════════════════════


@router.post("/scan", response_model=ScannedFieldsOut, status_code=status.HTTP_201_CREATED)
async def scan_document_endpoint(
    file: UploadFile = File(..., description="Passport or national ID image (JPEG/PNG/WEBP/PDF)"),
    document_type: str = "passport",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a passport or national ID scan.
    Extracts fields using the LLaVA vision model (or mock).
    Returns all extracted fields with per-field confidence scores.
    Fields below the low-confidence threshold are listed in `flagged_fields`.
    """
    if document_type not in ("passport", "national_id"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="document_type must be 'passport' or 'national_id'",
        )

    content_type = file.content_type or ""
    if content_type not in _SCAN_ALLOWED:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{content_type}'. Allowed: JPEG, PNG, WEBP, PDF.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 10 MB limit.",
        )

    try:
        doc = scan_document(
            file_bytes=file_bytes,
            original_filename=file.filename or "upload",
            document_type=document_type,
            user=current_user,
            db=db,
        )
    except Exception as exc:
        logger.exception("Scan failed for user %d: %s", current_user.id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document scanning failed. Please try again.",
        )

    return _build_scanned_fields_out(doc)


# ══════════════════════════════════════════════════════════════════════════════
# Form Filler — Step 8
# ══════════════════════════════════════════════════════════════════════════════


@router.post("/{doc_id}/fill", response_model=FilledFormOut)
async def fill_form_endpoint(
    doc_id: int,
    file: UploadFile = File(..., description="Blank visa form (PDF or DOCX)"),
    payload: FormFillRequest = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a blank visa application form (PDF or DOCX).
    The form is filled using personal data from:
      1. The `personal_data` field in the request body (if provided), OR
      2. The extracted fields from the Document specified by doc_id (must be a
         previously scanned passport belonging to the current user).

    Returns the filled form metadata. Download via GET /documents/{doc_id}/download.
    """
    # Resolve the source document
    source_doc = _get_doc_or_404(doc_id, current_user.id, db)

    content_type = file.content_type or ""
    # Normalise .docx MIME — browsers sometimes send different values
    filename = file.filename or "form"
    if filename.lower().endswith(".docx"):
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if content_type not in _FORM_ALLOWED:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported form format. Only PDF and DOCX are supported.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 10 MB limit.",
        )

    # Resolve personal data
    personal_data = payload.personal_data if payload and payload.personal_data else None
    if not personal_data:
        personal_data = _extract_personal_data_from_doc(source_doc)

    if not personal_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "No personal data available. Either provide personal_data in the request "
                "or reference a successfully scanned passport document."
            ),
        )

    # Create a new Document record for the form
    from app.services.scanner_service import _infer_mime, _save_upload
    form_doc = Document(
        user_id=current_user.id,
        filename=filename,
        file_path="",  # set after save
        file_type="visa_form",
        mime_type=_infer_mime(filename),
        extraction_status="done",
        fill_status="pending",
    )
    db.add(form_doc)
    db.flush()

    # Save the blank form to disk
    saved_path = _save_upload(file_bytes, filename, current_user.id)
    form_doc.file_path = str(saved_path)
    db.flush()

    try:
        filled_doc = fill_form(
            file_bytes=file_bytes,
            original_filename=filename,
            personal_data=personal_data,
            doc=form_doc,
            db=db,
        )
    except Exception as exc:
        logger.exception("Form fill failed for user %d: %s", current_user.id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Form filling failed. Please try again.",
        )

    return _build_filled_form_out(filled_doc)


# ══════════════════════════════════════════════════════════════════════════════
# List + Get + Download
# ══════════════════════════════════════════════════════════════════════════════


@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents for the current user."""
    return (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.get("/{doc_id}", response_model=ScannedFieldsOut)
def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific document with all extracted fields."""
    doc = _get_doc_or_404(doc_id, current_user.id, db)
    return _build_scanned_fields_out(doc)


@router.get("/{doc_id}/download")
def download_filled_form(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the filled form file for a document."""
    doc = _get_doc_or_404(doc_id, current_user.id, db)
    if not doc.filled_form_path or not Path(doc.filled_form_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No filled form available for this document.",
        )
    return FileResponse(
        path=doc.filled_form_path,
        filename=f"filled_{doc.filename}",
        media_type=doc.mime_type or "application/octet-stream",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _get_doc_or_404(doc_id: int, user_id: int, db: Session) -> Document:
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == user_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


def _extract_personal_data_from_doc(doc: Document) -> dict | None:
    """Pull the 'fields' dict out of a scanned document's extracted_data JSON."""
    if not doc.extracted_data or doc.extraction_status != "done":
        return None
    try:
        payload = json.loads(doc.extracted_data)
        return payload.get("fields")
    except (json.JSONDecodeError, AttributeError):
        return None


def _build_scanned_fields_out(doc: Document) -> ScannedFieldsOut:
    payload = {}
    if doc.extracted_data:
        try:
            payload = json.loads(doc.extracted_data)
        except json.JSONDecodeError:
            pass
    return ScannedFieldsOut(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        extraction_status=doc.extraction_status,
        extraction_confidence=doc.extraction_confidence,
        fields=payload.get("fields", {}),
        field_confidence=payload.get("field_confidence", {}),
        flagged_fields=payload.get("flagged_fields", []),
        low_confidence_threshold=payload.get("low_confidence_threshold", 0.75),
        created_at=doc.created_at,
    )


def _build_filled_form_out(doc: Document) -> FilledFormOut:
    payload = {}
    if doc.extracted_data:
        try:
            payload = json.loads(doc.extracted_data)
        except json.JSONDecodeError:
            pass
    fill_result = payload.get("fill_result", {})
    return FilledFormOut(
        id=doc.id,
        filename=doc.filename,
        fill_status=doc.fill_status,
        filled_form_path=doc.filled_form_path,
        filled_fields=fill_result.get("filled_fields", {}),
        unfilled_fields=fill_result.get("unfilled_fields", []),
        created_at=doc.created_at,
    )
