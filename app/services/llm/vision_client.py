"""
Vision client for image-based identity-document field extraction.
When VISION_MOCK=true: returns a realistic hardcoded extraction result.
When VISION_MOCK=false: base64-encodes the image and calls Ollama /api/chat with
LLaVA. (Independent of the text LLM provider, so the chat model can be OpenAI
while the scanner stays mocked until a real vision backend is wired up.)
"""

import base64
import json
import logging
import re
from pathlib import Path

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Public interface ───────────────────────────────────────────────────────────


def extract_fields_from_image(image_path: str, document_type: str) -> dict:
    """
    Send an image to the vision LLM and extract structured fields as a dict.
    Returns raw parsed JSON from the model.
    Raises RuntimeError on connection failure.
    """
    if settings.VISION_MOCK:
        return _mock_extraction(document_type)
    return _llava_extraction(image_path, document_type)


# ── Mock path ──────────────────────────────────────────────────────────────────

_MOCK_PASSPORT_DATA = {
    "document_type": "passport",
    "surname": "KHAN",
    "given_names": "AHMED RAZA",
    "nationality": "Pakistani",
    "passport_number": "AB1234567",
    "date_of_birth": "1995-03-14",
    "date_of_issue": "2019-06-01",
    "date_of_expiry": "2029-05-31",
    "place_of_birth": "Lahore",
    "gender": "M",
    "mrz_line_1": "P<PAKKHANAAHMED<<RAZA<<<<<<<<<<<<<<<<<<<<<",
    "mrz_line_2": "AB12345678PAK9503144M2905318<<<<<<<<<<<<4",
    "field_confidence": {
        "surname": 0.98,
        "given_names": 0.97,
        "nationality": 0.99,
        "passport_number": 0.96,
        "date_of_birth": 0.95,
        "date_of_expiry": 0.98,
        "place_of_birth": 0.82,
        "gender": 0.99,
        "mrz_line_1": 0.94,
        "mrz_line_2": 0.93,
    },
}

_MOCK_ID_DATA = {
    "document_type": "national_id",
    "surname": "KHAN",
    "given_names": "AHMED RAZA",
    "id_number": "42101-1234567-1",
    "date_of_birth": "1995-03-14",
    "date_of_expiry": "2029-05-31",
    "address": "House 12, Street 5, Gulberg III, Lahore",
    "field_confidence": {
        "surname": 0.97,
        "given_names": 0.96,
        "id_number": 0.94,
        "date_of_birth": 0.93,
        "date_of_expiry": 0.95,
        "address": 0.78,
    },
}


def _mock_extraction(document_type: str) -> dict:
    if document_type == "national_id":
        return _MOCK_ID_DATA.copy()
    return _MOCK_PASSPORT_DATA.copy()


# ── LLaVA path ─────────────────────────────────────────────────────────────────

_VISION_SYSTEM_PROMPT = """\
You are a document OCR specialist. Extract all visible fields from the provided
identity document image and return ONLY a valid JSON object. No markdown, no
explanation — just raw JSON.

For a passport, extract: surname, given_names, nationality, passport_number,
date_of_birth, date_of_issue, date_of_expiry, place_of_birth, gender,
mrz_line_1, mrz_line_2.

For a national ID, extract: surname, given_names, id_number, date_of_birth,
date_of_expiry, address, issuing_authority.

Also include a "field_confidence" object mapping each field name to a float
between 0.0 (very uncertain) and 1.0 (certain). Use lower values for blurry,
partially obscured, or ambiguous fields. Omit fields that are completely
unreadable — do not guess.

Date format: YYYY-MM-DD where possible. If uncertain about a digit, use '?'
in that position (e.g. "199?-03-14").
"""


def _llava_extraction(image_path: str, document_type: str) -> dict:
    image_data = _encode_image(image_path)
    mime_type = _infer_mime(image_path)

    payload = {
        "model": settings.OLLAMA_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_data}"},
                    },
                    {
                        "type": "text",
                        "text": (
                            f"Document type: {document_type}\n\n"
                            + _VISION_SYSTEM_PROMPT
                        ),
                    },
                ],
            }
        ],
        "stream": False,
    }

    try:
        with httpx.Client(timeout=180.0) as client:
            resp = client.post(f"{settings.OLLAMA_BASE_URL}/api/chat", json=payload)
            resp.raise_for_status()
    except httpx.ConnectError:
        raise RuntimeError(
            f"Cannot reach Ollama at {settings.OLLAMA_BASE_URL}. "
            "Is Ollama running with the llava model? Or set VISION_MOCK=true."
        )

    raw = resp.json()["message"]["content"]
    return _parse_vision_response(raw)


def _parse_vision_response(raw: str) -> dict:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    return json.loads(cleaned)


def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _infer_mime(image_path: str) -> str:
    suffix = Path(image_path).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(suffix, "image/jpeg")
