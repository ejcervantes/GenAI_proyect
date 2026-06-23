"""
Smart form filler service (Step 8).

fill_form() takes:
  - A blank PDF or DOCX visa application form (bytes)
  - A dict of personal data fields (from a prior passport scan or user input)
  - The Document record to update

Pipeline:
  1. Detect fillable fields in the form (PDF AcroForm or DOCX placeholders)
  2. Map personal data to detected fields using keyword matching + LLM assist
  3. Fill matched fields; leave unmatched fields highlighted/annotated
  4. Save the filled form and update Document.filled_form_path
"""

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.models.document import Document

logger = logging.getLogger(__name__)

FILLED_DIR = Path("uploads/filled_forms")

# ── Canonical field name aliases ───────────────────────────────────────────────
# Maps common form label patterns → canonical personal data keys

FIELD_ALIASES: dict[str, list[str]] = {
    "surname": ["surname", "last name", "family name", "lastname", "nachname"],
    "given_names": ["given name", "first name", "forename", "vorname", "given names"],
    "passport_number": ["passport no", "passport number", "travel document", "reisepass"],
    "date_of_birth": ["date of birth", "dob", "birth date", "geburtsdatum", "born on"],
    "date_of_expiry": ["expiry date", "expiration date", "valid until", "gültig bis"],
    "date_of_issue": ["date of issue", "issue date", "ausstellungsdatum"],
    "nationality": ["nationality", "citizenship", "staatsangehörigkeit"],
    "place_of_birth": ["place of birth", "birthplace", "geburtsort"],
    "gender": ["gender", "sex", "geschlecht"],
}


def fill_form(
    file_bytes: bytes,
    original_filename: str,
    personal_data: dict,
    doc: Document,
    db: Session,
) -> Document:
    """
    Fill a blank visa form with personal_data and save the result.
    Updates doc.filled_form_path and doc.fill_status.
    """
    suffix = Path(original_filename).suffix.lower()

    FILLED_DIR.mkdir(parents=True, exist_ok=True)
    out_name = f"{uuid.uuid4().hex}_filled{suffix}"
    out_path = FILLED_DIR / out_name

    try:
        if suffix == ".pdf":
            field_map, unfilled = _fill_pdf(file_bytes, personal_data, str(out_path))
        elif suffix in (".docx",):
            field_map, unfilled = _fill_docx(file_bytes, personal_data, str(out_path))
        else:
            raise ValueError(f"Unsupported form format: {suffix}. Only PDF and DOCX are supported.")
    except Exception as exc:
        logger.error("Form fill failed for doc #%d: %s", doc.id, exc)
        doc.fill_status = "failed"
        db.commit()
        raise

    doc.filled_form_path = str(out_path)
    doc.fill_status = "done"

    # Store fill metadata in extracted_data if not already present
    existing = json.loads(doc.extracted_data) if doc.extracted_data else {}
    existing["fill_result"] = {
        "filled_fields": field_map,
        "unfilled_fields": unfilled,
        "output_path": str(out_path),
    }
    doc.extracted_data = json.dumps(existing)

    db.commit()
    db.refresh(doc)

    logger.info(
        "Form fill complete for doc #%d: %d fields filled, %d unfilled",
        doc.id, len(field_map), len(unfilled),
    )
    return doc


# ── PDF filler ─────────────────────────────────────────────────────────────────


def _fill_pdf(
    file_bytes: bytes,
    personal_data: dict,
    out_path: str,
) -> tuple[dict, list[str]]:
    """
    Fill a PDF AcroForm using PyMuPDF.
    Returns (filled_field_map, list_of_unfilled_field_names).
    """
    import fitz  # PyMuPDF

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    field_map: dict[str, str] = {}
    unfilled: list[str] = []

    for page in doc:
        for widget in page.widgets():
            if widget.field_type not in (fitz.PDF_WIDGET_TYPE_TEXT, fitz.PDF_WIDGET_TYPE_COMBOBOX):
                continue

            label = (widget.field_label or widget.field_name or "").lower().strip()
            mapped_key = _match_field(label)

            if mapped_key and mapped_key in personal_data and personal_data[mapped_key]:
                value = str(personal_data[mapped_key])
                widget.field_value = value
                widget.update()
                field_map[widget.field_name or label] = value
            else:
                # Highlight unfilled fields with a yellow annotation
                unfilled.append(widget.field_name or label)
                annot = page.add_highlight_annot(widget.rect)
                annot.set_colors(stroke=(1, 0.9, 0))  # yellow
                annot.update()

    doc.save(out_path, garbage=3, deflate=True)
    doc.close()
    return field_map, unfilled


# ── DOCX filler ────────────────────────────────────────────────────────────────

# Match placeholders like {{surname}}, [SURNAME], <given_names>
_PLACEHOLDER_RE = re.compile(
    r"(\{\{([^}]+)\}\}|\[([A-Z_\s]+)\]|<([a-z_]+)>)",
    re.IGNORECASE,
)


def _fill_docx(
    file_bytes: bytes,
    personal_data: dict,
    out_path: str,
) -> tuple[dict, list[str]]:
    """
    Replace placeholder tokens in a DOCX form.
    Unfilled placeholders are wrapped in *** ... *** to visually flag them.
    Returns (filled_field_map, list_of_unfilled_placeholder_strings).
    """
    import io
    from docx import Document as DocxDocument
    from docx.shared import RGBColor

    doc = DocxDocument(io.BytesIO(file_bytes))
    field_map: dict[str, str] = {}
    unfilled: list[str] = []

    def _replace_in_paragraph(para) -> None:
        for run in para.runs:
            matches = list(_PLACEHOLDER_RE.finditer(run.text))
            if not matches:
                continue
            new_text = run.text
            for m in matches:
                placeholder_raw = m.group(0)
                # Extract the inner label from whichever group matched
                inner = (m.group(2) or m.group(3) or m.group(4) or "").strip()
                canonical = _match_field(inner.lower())
                if canonical and canonical in personal_data and personal_data[canonical]:
                    value = str(personal_data[canonical])
                    new_text = new_text.replace(placeholder_raw, value)
                    field_map[inner] = value
                else:
                    unfilled.append(placeholder_raw)
                    new_text = new_text.replace(placeholder_raw, f"***{placeholder_raw}***")
                    run.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)  # red for unfilled
            run.text = new_text

    for para in doc.paragraphs:
        _replace_in_paragraph(para)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    _replace_in_paragraph(para)

    doc.save(out_path)
    return field_map, unfilled


# ── Field matching ─────────────────────────────────────────────────────────────


def _match_field(label: str) -> Optional[str]:
    """
    Map a form field label to a canonical personal_data key.
    Returns None if no match found.
    """
    label = label.lower().strip()
    for canonical, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in label or label in alias:
                return canonical
    return None
