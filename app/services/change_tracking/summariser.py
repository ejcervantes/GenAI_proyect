"""
Change summariser.

Takes a DiffResult and generates two things via the LLM:
  1. A plain-language summary of what changed (for the ChangeAlert.summary field)
  2. An action_required string telling the user what they should do

With LLM_PROVIDER="mock" (or OpenAI unconfigured) the mock path returns
deterministic strings so the change-tracking pipeline can be tested end-to-end.
"""

import logging
from typing import Optional

from app.services.change_tracking.differ import DiffResult
from app.services.llm.llm_client import chat_completion

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a visa policy analyst. You will be given a diff showing changes to a visa policy document.
Write a short, plain-language summary (2–3 sentences max) explaining what changed and why it matters
to an applicant. Then write a one-sentence action recommendation starting with "You should...".

Respond in exactly this format — no extra text:
SUMMARY: <your 2-3 sentence summary>
ACTION: <your one-sentence action>
"""


def summarise_change(
    diff: DiffResult,
    passport_nationality: str,
    destination_country: str,
    travel_purpose: str,
) -> tuple[str, Optional[str]]:
    """
    Returns (summary_text, action_required_text).
    Falls back to a generic message if the LLM call fails.
    """
    added_preview = "\n".join(f"+ {l}" for l in diff.added_lines[:10])
    removed_preview = "\n".join(f"- {l}" for l in diff.removed_lines[:10])

    user_message = (
        f"Visa case: {passport_nationality} passport → {destination_country} ({travel_purpose})\n"
        f"Change type: {diff.change_type}\n\n"
        f"DIFF (+ added, - removed):\n{removed_preview}\n{added_preview}"
    )

    try:
        raw = chat_completion(system_prompt=_SYSTEM_PROMPT, user_message=user_message)
        return _parse_response(raw, diff, passport_nationality, destination_country, travel_purpose)
    except Exception as exc:
        logger.warning("Change summariser LLM call failed: %s", exc)
        return _fallback_summary(diff, passport_nationality, destination_country, travel_purpose)


def _parse_response(
    raw: str,
    diff: DiffResult,
    passport_nationality: str,
    destination_country: str,
    travel_purpose: str,
) -> tuple[str, Optional[str]]:
    summary: Optional[str] = None
    action: Optional[str] = None

    for line in raw.splitlines():
        if line.startswith("SUMMARY:"):
            summary = line[len("SUMMARY:"):].strip()
        elif line.startswith("ACTION:"):
            action = line[len("ACTION:"):].strip()

    if not summary:
        summary, action = _fallback_summary(diff, passport_nationality, destination_country, travel_purpose)

    return summary, action


def _fallback_summary(
    diff: DiffResult,
    passport_nationality: str,
    destination_country: str,
    travel_purpose: str,
) -> tuple[str, Optional[str]]:
    type_descriptions = {
        "fee_change": "Visa fees or cost-related information",
        "processing_time": "Processing times or appointment availability",
        "new_requirement": "Document requirements",
        "restriction": "Entry restrictions or visa issuance rules",
        "general": "Visa policy information",
    }
    description = type_descriptions.get(diff.change_type, "Visa policy information")
    summary = (
        f"{description} for {passport_nationality} nationals travelling to "
        f"{destination_country} for {travel_purpose} purposes has been updated. "
        f"Please review the latest requirements before proceeding with your application."
    )
    action = (
        f"You should check the latest requirements on the official {destination_country} "
        "embassy or consulate website before proceeding."
    )
    return summary, action
