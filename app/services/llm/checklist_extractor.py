"""
Checklist extractor — uses the LLM to parse visa policy chunks into a
structured list of document requirements.

The LLM is prompted to return JSON only, which is then parsed into
ChecklistItemData dataclasses. Falls back to a hardcoded minimal list
if the LLM call fails or returns unparseable output.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from app.services.llm.llm_client import chat_completion

logger = logging.getLogger(__name__)

# ── Data structure ─────────────────────────────────────────────────────────────


@dataclass
class ChecklistItemData:
    document_name: str
    description: str
    is_mandatory: bool = True
    is_conditional: bool = False
    condition_note: Optional[str] = None
    requires_translation: bool = False
    requires_notarization: bool = False
    order: int = 0


# ── System prompt ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a visa document checklist specialist. Given visa policy text, extract every
document requirement and return ONLY a valid JSON array. No markdown, no explanation,
no backticks — just the raw JSON array.

Each element must have these exact keys:
{
  "document_name": "short name of the document (e.g. 'Valid Passport')",
  "description": "one-sentence explanation of requirements or specifications",
  "is_mandatory": true or false,
  "is_conditional": true or false,
  "condition_note": "condition string or null",
  "requires_translation": true or false,
  "requires_notarization": true or false
}

Rules:
- is_mandatory=true for documents required in all cases.
- is_conditional=true when the document is only needed in specific circumstances;
  set condition_note to explain when.
- requires_translation=true if the document must be translated into the
  destination country's official language.
- requires_notarization=true if official certification or notarization is mentioned.
- Deduplicate: if the same document appears multiple times, include it once.
- Order: put mandatory items first, conditional items last.
- If no documents can be extracted, return an empty array: []
"""


# ── Public function ────────────────────────────────────────────────────────────


def extract_checklist_items(
    context: str,
    passport_nationality: str,
    destination_country: str,
    travel_purpose: str,
) -> list[ChecklistItemData]:
    """
    Ask the LLM to extract checklist items from the retrieved context.
    Returns a list of ChecklistItemData, ordered mandatory-first.
    Falls back to an empty list on parse failure.
    """
    user_message = (
        f"Passport nationality: {passport_nationality}\n"
        f"Destination country: {destination_country}\n"
        f"Travel purpose: {travel_purpose}\n\n"
        f"VISA POLICY TEXT:\n{context}\n\n"
        "Extract all document requirements as a JSON array."
    )

    try:
        raw = chat_completion(system_prompt=_SYSTEM_PROMPT, user_message=user_message)
        items = _parse_llm_response(raw)
    except Exception as exc:
        logger.warning("Checklist LLM extraction failed: %s — using fallback", exc)
        items = _fallback_items(passport_nationality, destination_country, travel_purpose)

    # Assign order: mandatory first, then conditional
    mandatory = [i for i in items if i.is_mandatory and not i.is_conditional]
    conditional = [i for i in items if i.is_conditional]
    optional = [i for i in items if not i.is_mandatory and not i.is_conditional]

    ordered = mandatory + conditional + optional
    for idx, item in enumerate(ordered):
        item.order = idx

    return ordered


# ── Parsing ────────────────────────────────────────────────────────────────────


def _parse_llm_response(raw: str) -> list[ChecklistItemData]:
    """
    Strip any accidental markdown fences and parse the JSON array.
    Raises ValueError if the result is not a list.
    """
    cleaned = raw.strip()
    # Strip ```json ... ``` or ``` ... ``` fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    data = json.loads(cleaned)
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array, got {type(data)}")

    items: list[ChecklistItemData] = []
    for entry in data:
        if not isinstance(entry, dict) or "document_name" not in entry:
            continue
        items.append(
            ChecklistItemData(
                document_name=entry.get("document_name", "Unknown Document"),
                description=entry.get("description", ""),
                is_mandatory=bool(entry.get("is_mandatory", True)),
                is_conditional=bool(entry.get("is_conditional", False)),
                condition_note=entry.get("condition_note") or None,
                requires_translation=bool(entry.get("requires_translation", False)),
                requires_notarization=bool(entry.get("requires_notarization", False)),
            )
        )
    return items


# ── Fallback ───────────────────────────────────────────────────────────────────


def _fallback_items(
    passport_nationality: str,
    destination_country: str,
    travel_purpose: str,
) -> list[ChecklistItemData]:
    """
    Minimal universal fallback when LLM parsing fails completely.
    These items are true for virtually every visa application.
    """
    logger.warning(
        "Using fallback checklist items for %s → %s (%s)",
        passport_nationality,
        destination_country,
        travel_purpose,
    )
    return [
        ChecklistItemData(
            document_name="Valid Passport",
            description="Passport must be valid for at least 6 months beyond your intended stay.",
            is_mandatory=True,
        ),
        ChecklistItemData(
            document_name="Completed Visa Application Form",
            description="Official application form for the destination country, fully completed and signed.",
            is_mandatory=True,
        ),
        ChecklistItemData(
            document_name="Recent Biometric Photographs",
            description="Passport-sized photos meeting the embassy's specification (typically 35×45mm, white background).",
            is_mandatory=True,
        ),
        ChecklistItemData(
            document_name="Proof of Financial Means",
            description="Bank statements (last 3–6 months) or sponsorship letter demonstrating ability to cover costs.",
            is_mandatory=True,
        ),
        ChecklistItemData(
            document_name="Travel Itinerary / Flight Booking",
            description="Confirmed or provisional flight reservation showing entry and exit dates.",
            is_mandatory=True,
        ),
        ChecklistItemData(
            document_name="Travel Health Insurance",
            description="Insurance policy valid in the destination country, minimum coverage as required by embassy.",
            is_mandatory=True,
        ),
    ]
