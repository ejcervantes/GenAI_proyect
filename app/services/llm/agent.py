"""
PassportAI Conversational Q&A Agent.

Flow for each question:
  1. Decide which tools to call based on question content
  2. Call tools → retrieve relevant chunks from ChromaDB
  3. Build a structured prompt (system + context + question)
  4. Call LLM → get answer text
  5. Compute confidence score from chunk relevance + coverage heuristics
  6. Return AgentResponse with answer, confidence, citations, and metadata
"""

import inspect
import logging
import re
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings
from app.services.llm.llm_client import (
    chat_completion,
    chat_with_tools,
    resolved_provider,
)
from app.services.llm.tools import (
    TOOL_FUNCTIONS,
    TOOL_SCHEMAS,
    Citation,
    ToolResult,
    check_visa_free_access,
    get_processing_time,
    get_visa_requirements,
)

logger = logging.getLogger(__name__)

# ── Response dataclass ─────────────────────────────────────────────────────────


@dataclass
class AgentResponse:
    answer: str
    confidence_score: float          # 0.0 – 1.0
    citations: list[Citation]
    chunks_retrieved: int
    tools_used: list[str]
    model_used: str
    was_mocked: bool


# ── System prompt ──────────────────────────────────────────────────────────────

_DISCLAIMER_LINE = (
    "⚠️ Visa rules change frequently. Verify all requirements directly with the "
    "relevant embassy or consulate before applying."
)

# Prompt for the heuristic path: context is injected into the message directly.
SYSTEM_PROMPT = f"""\
You are PassportAI, a specialist visa and immigration assistant for international students and travellers.

Your job is to answer questions about visa requirements, application procedures, required documents,
processing times, and entry rules using ONLY the context provided below.

Rules:
- Answer factually and specifically. Cite numbered sources like [1], [2] from the context.
- If the context does not contain enough information to answer, say so clearly — do not invent facts.
- Always end your answer with this exact disclaimer on its own line:
  {_DISCLAIMER_LINE}
- Keep answers concise but complete. Use bullet points for document lists.
- Do not speculate about information not present in the context.
"""

# Prompt for the function-calling path: the model retrieves context via tools.
FUNCTION_CALLING_SYSTEM_PROMPT = f"""\
You are PassportAI, a specialist visa and immigration assistant for international students and travellers.

You have tools that retrieve visa-policy information from a trusted, source-cited knowledge base.
ALWAYS call the relevant tool(s) before answering a visa question — never answer factual visa
questions from your own memory. Choose the most relevant tool(s) and infer their arguments
(passport nationality, destination country, travel purpose) from the user's question and the
known context. You may call multiple tools.

After the tools return, answer using ONLY their content. Rules:
- Be factual and specific; do not invent facts not present in the retrieved content.
- If the tools return no relevant information, say so clearly and suggest contacting the embassy.
- Use bullet points for document lists.
- Always end your answer with this exact disclaimer on its own line:
  {_DISCLAIMER_LINE}
"""


# ── Agent ──────────────────────────────────────────────────────────────────────


def ask(
    question: str,
    passport_nationality: Optional[str] = None,
    destination_country: Optional[str] = None,
    travel_purpose: Optional[str] = None,
) -> AgentResponse:
    """
    Main entry point. Ask a visa question and get a structured answer.

    With an OpenAI provider, the LLM drives real function-calling: it picks the
    tools and infers their arguments. Otherwise (mock / ollama) we fall back to
    the regex-based tool selector so the app still works offline.
    """
    provider = resolved_provider()

    try:
        if provider == "openai":
            answer, tool_results = _ask_with_function_calling(
                question, passport_nationality, destination_country, travel_purpose
            )
        else:
            answer, tool_results = _ask_with_heuristics(
                question, passport_nationality, destination_country, travel_purpose
            )
    except RuntimeError as exc:
        logger.error("LLM call failed: %s", exc)
        answer = (
            "I was unable to generate an answer at this time due to an LLM service error. "
            f"Please try again later.\n\n{_DISCLAIMER_LINE}"
        )
        tool_results = []

    # Aggregate citations / coverage / confidence from whatever tools actually ran.
    all_chunks = sum(r.chunks_retrieved for r in tool_results)
    all_citations = _deduplicate_citations([c for r in tool_results for c in r.citations])
    tools_used = [r.tool_name for r in tool_results]
    avg_relevances = [r.avg_relevance for r in tool_results if r.avg_relevance > 0]
    confidence = _compute_confidence(
        avg_relevances=avg_relevances,
        chunks_retrieved=all_chunks,
        answer=answer,
    )

    model_name = {
        "openai": settings.OPENAI_CHAT_MODEL,
        "ollama": settings.OLLAMA_MODEL,
        "mock": "mock",
    }.get(provider, provider)

    return AgentResponse(
        answer=answer,
        confidence_score=confidence,
        citations=all_citations,
        chunks_retrieved=all_chunks,
        tools_used=tools_used,
        model_used=model_name,
        was_mocked=provider == "mock",
    )


# ── Function-calling path (OpenAI) ──────────────────────────────────────────────


def _ask_with_function_calling(
    question: str,
    passport_nationality: Optional[str],
    destination_country: Optional[str],
    travel_purpose: Optional[str],
) -> tuple[str, list[ToolResult]]:
    """
    Let the LLM choose tools and infer arguments. Each tool call is executed here,
    its ToolResult recorded (for citations/confidence), and its text fed back to
    the model by chat_with_tools.
    """
    collected: list[ToolResult] = []

    def run_tool(name: str, args: dict) -> str:
        fn = TOOL_FUNCTIONS.get(name)
        if fn is None:
            return f"Unknown tool '{name}'."
        filled = _with_profile_defaults(
            args, passport_nationality, destination_country, travel_purpose
        )
        kwargs = {k: v for k, v in filled.items() if k in inspect.signature(fn).parameters}
        result = fn(**kwargs)
        collected.append(result)
        return result.context_text

    user_message = _build_question_message(
        question, passport_nationality, destination_country, travel_purpose
    )
    answer = chat_with_tools(
        system_prompt=FUNCTION_CALLING_SYSTEM_PROMPT,
        user_message=user_message,
        tools=TOOL_SCHEMAS,
        run_tool=run_tool,
    )
    return answer, collected


def _with_profile_defaults(
    args: dict,
    passport_nationality: Optional[str],
    destination_country: Optional[str],
    travel_purpose: Optional[str],
) -> dict:
    """Fill any tool argument the model omitted (or left blank) from the known profile."""
    out = dict(args)
    if not out.get("passport_nationality"):
        out["passport_nationality"] = passport_nationality or "general"
    if not out.get("destination_country"):
        out["destination_country"] = destination_country or ""
    if not out.get("travel_purpose"):
        out["travel_purpose"] = travel_purpose or "general"
    return out


def _build_question_message(
    question: str,
    passport_nationality: Optional[str],
    destination_country: Optional[str],
    travel_purpose: Optional[str],
) -> str:
    known = []
    if passport_nationality:
        known.append(f"- Passport nationality: {passport_nationality}")
    if destination_country:
        known.append(f"- Destination country: {destination_country}")
    if travel_purpose:
        known.append(f"- Travel purpose: {travel_purpose}")
    known_block = ("Known context (use as defaults):\n" + "\n".join(known) + "\n\n") if known else ""
    return f"{known_block}Question: {question}"


# ── Heuristic path (mock / ollama fallback) ─────────────────────────────────────


def _ask_with_heuristics(
    question: str,
    passport_nationality: Optional[str],
    destination_country: Optional[str],
    travel_purpose: Optional[str],
) -> tuple[str, list[ToolResult]]:
    """Regex-based tool selection + a single LLM call. Used when not on OpenAI."""
    tool_results = _select_and_run_tools(
        question, passport_nationality, destination_country, travel_purpose
    )
    combined_context = "\n\n---\n\n".join(r.context_text for r in tool_results)
    user_message = _build_user_message(
        combined_context,
        question,
        passport_nationality,
        destination_country,
        travel_purpose,
    )
    answer = chat_completion(system_prompt=SYSTEM_PROMPT, user_message=user_message)
    return answer, tool_results


# ── Tool selection ─────────────────────────────────────────────────────────────

_VISA_FREE_SIGNALS = re.compile(
    r"\b(visa[- ]free|no visa|without visa|waiver|esta|eta|exempt)\b", re.IGNORECASE
)
_PROCESSING_SIGNALS = re.compile(
    r"\b(how long|processing time|wait|weeks|days|when|timeline|appointment|interview)\b",
    re.IGNORECASE,
)


def _select_and_run_tools(
    question: str,
    passport_nationality: Optional[str],
    destination_country: Optional[str],
    travel_purpose: Optional[str],
) -> list[ToolResult]:
    """
    Heuristically choose which tools to invoke.
    Always calls get_visa_requirements as the base tool.
    Adds check_visa_free_access if the question is about visa-free entry.
    Adds get_processing_time if the question is about timelines.
    """
    results: list[ToolResult] = []

    # Base tool: always run
    results.append(
        get_visa_requirements(
            passport_nationality=passport_nationality or "general",
            destination_country=destination_country or "",
            travel_purpose=travel_purpose or "general",
        )
    )

    # Visa-free access
    if _VISA_FREE_SIGNALS.search(question):
        results.append(
            check_visa_free_access(
                passport_nationality=passport_nationality or "general",
                destination_country=destination_country or "",
            )
        )

    # Processing time
    if _PROCESSING_SIGNALS.search(question):
        results.append(
            get_processing_time(
                passport_nationality=passport_nationality or "general",
                destination_country=destination_country or "",
                travel_purpose=travel_purpose or "general",
            )
        )

    return results


# ── Prompt construction ────────────────────────────────────────────────────────


def _build_user_message(
    context: str,
    question: str,
    passport_nationality: Optional[str],
    destination_country: Optional[str],
    travel_purpose: Optional[str],
) -> str:
    meta_lines = []
    if passport_nationality:
        meta_lines.append(f"- Passport nationality: {passport_nationality}")
    if destination_country:
        meta_lines.append(f"- Destination country: {destination_country}")
    if travel_purpose:
        meta_lines.append(f"- Travel purpose: {travel_purpose}")

    meta_block = ("\nUSER CONTEXT:\n" + "\n".join(meta_lines) + "\n") if meta_lines else ""

    return f"""{meta_block}
CONTEXT:
{context}

QUESTION:
{question}
"""


# ── Confidence scoring ─────────────────────────────────────────────────────────


def _compute_confidence(
    avg_relevances: list[float],
    chunks_retrieved: int,
    answer: str,
) -> float:
    """
    Heuristic confidence score (0.0–1.0).

    Factors:
    - Mean chunk relevance from semantic search (primary signal)
    - Whether enough chunks were retrieved (coverage)
    - Whether the answer contains "not found" / "insufficient" phrases (penalty)
    """
    if not avg_relevances or chunks_retrieved == 0:
        return 0.0

    base = sum(avg_relevances) / len(avg_relevances)

    # Coverage bonus: more chunks = more evidence
    coverage_bonus = min(0.1, chunks_retrieved * 0.02)

    # Low-confidence signal in the answer itself
    low_confidence_phrases = [
        "not found", "no information", "insufficient", "cannot answer",
        "don't have", "do not have", "unable to find",
    ]
    penalty = 0.2 if any(p in answer.lower() for p in low_confidence_phrases) else 0.0

    score = base + coverage_bonus - penalty
    return round(max(0.0, min(1.0, score)), 4)


# ── Citation deduplication ─────────────────────────────────────────────────────


def _deduplicate_citations(citations: list[Citation]) -> list[Citation]:
    """Remove duplicate citations (same source URL)."""
    seen: set[str] = set()
    unique: list[Citation] = []
    for c in citations:
        if c.source not in seen:
            seen.add(c.source)
            unique.append(c)
    return unique
