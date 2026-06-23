"""
Policy differ.

Compares two versions of a policy text and returns a structured DiffResult
describing what changed. Uses difflib for the raw diff and a set of heuristics
to classify the change type and severity — no LLM needed at this stage.
The LLM summarises the diff in plain language in a later step.
"""

import difflib
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class DiffResult:
    has_changes: bool
    added_lines: list[str]
    removed_lines: list[str]
    raw_diff: str                  # unified diff string for storage
    change_type: str               # new_requirement | fee_change | processing_time | restriction | general
    severity: str                  # info | warning | critical


_NO_CHANGE = DiffResult(
    has_changes=False,
    added_lines=[],
    removed_lines=[],
    raw_diff="",
    change_type="general",
    severity="info",
)


def compute_diff(old_text: str, new_text: str) -> DiffResult:
    """
    Compute a structured diff between old_text and new_text.
    Returns a DiffResult with has_changes=False if texts are semantically equal.
    """
    # Split WITHOUT keepends and pair with lineterm="" so each diff line is
    # newline-free; we then re-join with "\n". (Joining lineterm="" output with
    # "" merges every line into one — which silently broke +/- detection and
    # meant real single-paragraph policy changes were never flagged.)
    old_lines = _normalise(old_text).split("\n")
    new_lines = _normalise(new_text).split("\n")

    if old_lines == new_lines:
        return _NO_CHANGE

    raw = "\n".join(
        difflib.unified_diff(old_lines, new_lines, fromfile="previous", tofile="current", lineterm="")
    )

    added = [l[1:].strip() for l in raw.splitlines() if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:].strip() for l in raw.splitlines() if l.startswith("-") and not l.startswith("---")]

    if not added and not removed:
        return _NO_CHANGE

    change_type = _classify_change_type(added, removed)
    severity = _classify_severity(added, removed, change_type)

    return DiffResult(
        has_changes=True,
        added_lines=added,
        removed_lines=removed,
        raw_diff=raw[:4000],   # cap stored diff at 4k chars
        change_type=change_type,
        severity=severity,
    )


# ── Classification helpers ─────────────────────────────────────────────────────

# Patterns match word *stems* (no trailing \b) so inflections are caught too,
# e.g. "suspend" → suspended/suspension, "cancel" → cancelled/cancellation.
_FEE_PATTERN = re.compile(r"\b(fee|€|EUR|USD|\$|£|GBP|cost|price|charge)", re.IGNORECASE)
_TIME_PATTERN = re.compile(r"\b(week|day|month|processing|timeline|appointment|wait)", re.IGNORECASE)
_RESTRICT_PATTERN = re.compile(
    r"\b(ban|suspend|restrict|cancel|revok|refus|reject|no longer)", re.IGNORECASE
)
_REQUIRE_PATTERN = re.compile(r"\b(require|must|mandatory|needed|compulsory|submit|provide)", re.IGNORECASE)


def _classify_change_type(added: list[str], removed: list[str]) -> str:
    all_changed = " ".join(added + removed)
    # Restrictions first — they are the highest-impact change and may coincide
    # with fee/time wording ("cancelled this month") that would otherwise win.
    if _RESTRICT_PATTERN.search(all_changed):
        return "restriction"
    if _FEE_PATTERN.search(all_changed):
        return "fee_change"
    if _TIME_PATTERN.search(all_changed):
        return "processing_time"
    if _REQUIRE_PATTERN.search(all_changed):
        return "new_requirement"
    return "general"


def _classify_severity(added: list[str], removed: list[str], change_type: str) -> str:
    all_changed = " ".join(added + removed).lower()

    # Critical: outright bans, suspension of visa issuance, or a long list of new requirements
    if _RESTRICT_PATTERN.search(all_changed) or len(added) > 8:
        return "critical"

    # Warning: fee increases, new mandatory documents, processing time jumps
    if change_type in ("fee_change", "new_requirement", "processing_time"):
        return "warning"

    return "info"


# ── Normalisation ──────────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Strip extra whitespace so cosmetic reformatting doesn't register as a change."""
    lines = [l.strip() for l in text.splitlines()]
    return "\n".join(l for l in lines if l)
