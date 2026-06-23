"""
Document scanner service.

scan_document() is called by the endpoint after the file has been uploaded.
It:
  1. Saves the uploaded file to disk
  2. Calls the vision LLM to extract fields
  3. Computes an overall confidence score and flags low-confidence fields
  4. Persists the result to the Document model
  5. Returns the Document ORM object

Supported input formats: JPEG, PNG, WEBP (image files only for the scanner).
PDF passport scans are rasterized to PNG first via PyMuPDF.
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.user import User
from app.services.llm.vision_client import extract_fields_from_image

logger = logging.getLogger(__name__)

# Where uploaded files are stored (relative to project root)
UPLOAD_DIR = Path("uploads")
LOW_CONFIDENCE_THRESHOLD = 0.75  # fields below this are flagged


def scan_document(
    file_bytes: bytes,
    original_filename: str,
    document_type: str,
    user: User,
    db: Session,
) -> Document:
    """
    Full scan pipeline: save file → extract fields → persist → return Document.
    document_type must be one of: "passport", "national_id"
    """
    # 1. Save to disk
    file_path = _save_upload(file_bytes, original_filename, user.id)

    # 2. If PDF, rasterise first page to PNG
    working_path = str(file_path)
    if original_filename.lower().endswith(".pdf"):
        working_path = _rasterise_pdf(str(file_path))

    # 3. Create Document record (pending)
    doc = Document(
        user_id=user.id,
        filename=original_filename,
        file_path=str(file_path),
        file_type=document_type,
        mime_type=_infer_mime(original_filename),
        extraction_status="processing",
    )
    db.add(doc)
    db.flush()

    # 4. Run vision extraction
    try:
        raw_fields = extract_fields_from_image(working_path, document_type)
    except Exception as exc:
        logger.error("Vision extraction failed for doc #%d: %s", doc.id, exc)
        doc.extraction_status = "failed"
        db.commit()
        raise

    # 5. Separate field_confidence from data fields
    field_confidence: dict = raw_fields.pop("field_confidence", {})
    # Remove meta fields that aren't data fields
    raw_fields.pop("document_type", None)

    # 6. Flag low-confidence fields
    flagged_fields = [
        field for field, score in field_confidence.items()
        if score < LOW_CONFIDENCE_THRESHOLD
    ]
    overall_confidence = (
        round(sum(field_confidence.values()) / len(field_confidence), 4)
        if field_confidence else 0.5
    )

    # 7. Build extracted_data payload
    extracted_payload = {
        "fields": raw_fields,
        "field_confidence": field_confidence,
        "flagged_fields": flagged_fields,
        "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
    }

    # 8. Persist results
    doc.extracted_data = json.dumps(extracted_payload)
    doc.extraction_confidence = overall_confidence
    doc.extraction_status = "done"
    db.commit()
    db.refresh(doc)

    logger.info(
        "Document #%d scanned: %d fields, overall_confidence=%.2f, flagged=%s",
        doc.id, len(raw_fields), overall_confidence, flagged_fields,
    )
    return doc


# ── Helpers ────────────────────────────────────────────────────────────────────


def _save_upload(file_bytes: bytes, original_filename: str, user_id: int) -> Path:
    user_dir = UPLOAD_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    # Prefix with a UUID to avoid collisions
    safe_name = f"{uuid.uuid4().hex}_{Path(original_filename).name}"
    dest = user_dir / safe_name
    dest.write_bytes(file_bytes)
    return dest


def _rasterise_pdf(pdf_path: str, dpi: int = 200) -> str:
    """
    Convert the first page of a PDF to a PNG using PyMuPDF.
    Returns the path to the PNG file.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    page = doc[0]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    out_path = pdf_path.replace(".pdf", "_page1.png")
    pix.save(out_path)
    doc.close()
    return out_path


def _infer_mime(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
    }.get(suffix, "application/octet-stream")
