"""
Typed tool definitions for the Q&A agent.

Each tool is a plain Python function that:
  1. Calls search_chunks() with the right query and metadata filters
  2. Returns a structured ToolResult containing retrieved text + citations

The agent in agent.py calls these tools, inspects their results,
and decides which to present to the LLM.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

# search_chunks deferred — importing it at the top pulls in chroma_client →
# chromadb. Keeping it lazy avoids loading the vector store at import time.

logger = logging.getLogger(__name__)

TOP_K = 5  # chunks to retrieve per tool call


@dataclass
class Citation:
    title: str
    source: str
    last_scraped: str
    relevance_score: float


@dataclass
class ToolResult:
    tool_name: str
    context_text: str  # concatenated chunk texts passed to the LLM
    citations: list[Citation]
    chunks_retrieved: int
    avg_relevance: float  # mean relevance of retrieved chunks (0–1)


# ── Tool implementations ──────────────────────────────────────────────────────


def get_visa_requirements(
    passport_nationality: str,
    destination_country: str,
    travel_purpose: str,
) -> ToolResult:
    """
    Retrieve general visa requirements for a given passport/destination/purpose triple.
    Covers required documents, application procedure, fees, and key conditions.
    """
    query = (
        f"visa requirements {passport_nationality} passport {destination_country} "
        f"{travel_purpose} documents needed application process"
    )
    return _run_search(
        "get_visa_requirements",
        query,
        passport_nationality,
        destination_country,
        travel_purpose,
    )


def check_visa_free_access(
    passport_nationality: str,
    destination_country: str,
) -> ToolResult:
    """
    Check whether the given passport nationality has visa-free or visa-on-arrival
    access to the destination country, and under what conditions.
    """
    query = (
        f"visa free access {passport_nationality} {destination_country} "
        "no visa required entry without visa waiver program ESTA eTA"
    )
    return _run_search(
        "check_visa_free_access",
        query,
        passport_nationality,
        destination_country,
        travel_purpose=None,  # visa-free status is purpose-agnostic
    )


def get_processing_time(
    passport_nationality: str,
    destination_country: str,
    travel_purpose: str,
) -> ToolResult:
    """
    Retrieve expected visa processing times, interview wait times,
    and any expedite options.
    """
    query = (
        f"visa processing time {passport_nationality} {destination_country} "
        f"{travel_purpose} weeks appointment wait interview timeline"
    )
    return _run_search(
        "get_processing_time",
        query,
        passport_nationality,
        destination_country,
        travel_purpose,
    )


def get_document_checklist(
    passport_nationality: str,
    destination_country: str,
    travel_purpose: str = "general",
) -> ToolResult:
    """
    Retrieve the list of required documents for a passport/destination/purpose
    so the agent can present an ordered checklist.
    """
    query = (
        f"required documents checklist {passport_nationality} {destination_country} "
        f"{travel_purpose} application documents needed list bring submit"
    )
    return _run_search(
        "get_document_checklist",
        query,
        passport_nationality,
        destination_country,
        travel_purpose,
    )


def get_student_permit_guidance(
    passport_nationality: str,
    destination_country: str,
) -> ToolResult:
    """
    Retrieve student-specific guidance: study visa, blocked account, enrolment,
    residence permit, and post-study work authorisation.
    """
    query = (
        f"student visa residence permit blocked account enrolment registration "
        f"post-study work {passport_nationality} {destination_country} university"
    )
    return _run_search(
        "get_student_permit_guidance",
        query,
        passport_nationality,
        destination_country,
        travel_purpose="student",
    )


# ── Internal helper ────────────────────────────────────────────────────────────


def _run_search(
    tool_name: str,
    query: str,
    passport_nationality: Optional[str],
    destination_country: Optional[str],
    travel_purpose: Optional[str],
) -> ToolResult:
    from app.services.rag.search import search_chunks

    chunks = search_chunks(
        query=query,
        passport_nationality=passport_nationality,
        destination_country=destination_country,
        travel_purpose=travel_purpose,
        top_k=TOP_K,
    )

    if not chunks:
        return ToolResult(
            tool_name=tool_name,
            context_text="No relevant visa policy information was found for this query.",
            citations=[],
            chunks_retrieved=0,
            avg_relevance=0.0,
        )

    context_parts = []
    citations = []
    scores = []

    for i, chunk in enumerate(chunks, start=1):
        meta = chunk["metadata"]
        context_parts.append(f"[{i}] {chunk['text']}")
        citations.append(
            Citation(
                title=meta.get("title", "Unknown"),
                source=meta.get("source", ""),
                last_scraped=meta.get("last_scraped", ""),
                relevance_score=chunk["relevance_score"],
            )
        )
        scores.append(chunk["relevance_score"])

    avg = round(sum(scores) / len(scores), 4) if scores else 0.0

    return ToolResult(
        tool_name=tool_name,
        context_text="\n\n".join(context_parts),
        citations=citations,
        chunks_retrieved=len(chunks),
        avg_relevance=avg,
    )


# ── Tool registry (single source of truth) ─────────────────────────────────────
# TOOL_FUNCTIONS maps a tool name → its Python callable (used to execute it).
# TOOL_SCHEMAS is the OpenAI function-calling spec the LLM sees (used to let the
# model choose tools and infer arguments). Both are derived from the same names,
# so adding a tool means editing one place.

TOOL_FUNCTIONS = {
    "get_visa_requirements": get_visa_requirements,
    "check_visa_free_access": check_visa_free_access,
    "get_processing_time": get_processing_time,
    "get_document_checklist": get_document_checklist,
    "get_student_permit_guidance": get_student_permit_guidance,
}

_PURPOSE_ENUM = ["student", "work", "tourist", "family", "general"]


def _tool(name: str, description: str, props: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


_PASSPORT = {"type": "string", "description": "Traveller's passport nationality, e.g. 'Pakistani'."}
_DESTINATION = {"type": "string", "description": "Destination country, e.g. 'Germany'."}
_PURPOSE = {"type": "string", "enum": _PURPOSE_ENUM, "description": "Reason for travel."}

TOOL_SCHEMAS = [
    _tool(
        "get_visa_requirements",
        "Required documents, fees, and application procedure for a passport/destination/purpose.",
        {"passport_nationality": _PASSPORT, "destination_country": _DESTINATION, "travel_purpose": _PURPOSE},
        ["destination_country"],
    ),
    _tool(
        "check_visa_free_access",
        "Whether a nationality has visa-free or visa-on-arrival access to a destination, and conditions.",
        {"passport_nationality": _PASSPORT, "destination_country": _DESTINATION},
        ["destination_country"],
    ),
    _tool(
        "get_processing_time",
        "Expected visa processing times, appointment/interview waits, and expedite options.",
        {"passport_nationality": _PASSPORT, "destination_country": _DESTINATION, "travel_purpose": _PURPOSE},
        ["destination_country"],
    ),
    _tool(
        "get_document_checklist",
        "The ordered list of documents required for a passport/destination/purpose application.",
        {"passport_nationality": _PASSPORT, "destination_country": _DESTINATION, "travel_purpose": _PURPOSE},
        ["destination_country"],
    ),
    _tool(
        "get_student_permit_guidance",
        "Student-specific guidance: study visa, blocked account, enrolment, residence permit, post-study work.",
        {"passport_nationality": _PASSPORT, "destination_country": _DESTINATION},
        ["destination_country"],
    ),
]
