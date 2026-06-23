"""
LLM service — text generation for the agent, checklist extractor and summariser.

Provider is selected by settings.LLM_PROVIDER:
  "openai" → OpenAI Chat Completions (default). Falls back to the mock if no
             OPENAI_API_KEY is configured, so the app never hard-crashes.
  "ollama" → local Ollama /api/chat.
  "mock"   → deterministic stub for CI / offline dev.
"""

import json
import logging
from typing import Callable

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def resolved_provider() -> str:
    """
    The provider actually in effect. "openai" without a key degrades to "mock"
    so callers (and the agent's model/was_mocked metadata) stay accurate.
    """
    provider = (settings.LLM_PROVIDER or "mock").lower()
    if provider == "openai" and not settings.OPENAI_API_KEY:
        return "mock"
    return provider


# ── Public interface ───────────────────────────────────────────────────────────


def chat_completion(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.2,
) -> str:
    """
    Send a chat message to the LLM and return the assistant reply as a string.
    """
    provider = resolved_provider()
    if provider == "openai":
        return _openai_completion(system_prompt, user_message, temperature)
    if provider == "ollama":
        return _ollama_completion(system_prompt, user_message, temperature)
    return _mock_completion(system_prompt, user_message)


# ── Mock path ──────────────────────────────────────────────────────────────────

_MOCK_ANSWER_TEMPLATE = """\
Based on the available visa policy information, here is what you need to know:

{context_summary}

**Important:** Visa requirements change frequently. Always verify this information
directly with the relevant embassy or consulate before making travel arrangements.
This answer is based on policy documents last updated as noted in the sources.
"""


def _mock_completion(system_prompt: str, user_message: str) -> str:
    """
    Return a plausible-looking mock response.
    Extracts key terms from the user message to personalise the stub.
    """
    # Pull context block out of the user message if present
    if "CONTEXT:" in user_message:
        context_part = user_message.split("CONTEXT:")[1].split("QUESTION:")[0].strip()
        # Summarise: take the first 300 chars of the context
        summary = context_part[:300] + ("..." if len(context_part) > 300 else "")
    else:
        summary = "The provided context contains relevant visa policy information for your query."

    return _MOCK_ANSWER_TEMPLATE.format(context_summary=summary)


# ── OpenAI path ────────────────────────────────────────────────────────────────


def _openai_post(client: httpx.Client, payload: dict) -> dict:
    """POST a payload to OpenAI chat/completions; return parsed JSON or raise."""
    try:
        resp = client.post(
            f"{settings.OPENAI_BASE_URL}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"OpenAI chat returned HTTP {exc.response.status_code}: {exc.response.text}"
        ) from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"OpenAI chat request failed: {exc}") from exc
    return resp.json()


def _openai_completion(
    system_prompt: str,
    user_message: str,
    temperature: float,
) -> str:
    """
    POST to the OpenAI Chat Completions endpoint and return the reply text.
    Raises RuntimeError on transport/HTTP failure so callers can degrade.
    """
    payload = {
        "model": settings.OPENAI_CHAT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
    }
    with httpx.Client(timeout=120.0) as client:
        data = _openai_post(client, payload)
    return data["choices"][0]["message"]["content"]


# ── OpenAI function-calling loop ────────────────────────────────────────────────


def chat_with_tools(
    system_prompt: str,
    user_message: str,
    tools: list[dict],
    run_tool: Callable[[str, dict], str],
    temperature: float = 0.2,
    max_iters: int = 4,
) -> str:
    """
    Run an OpenAI tool-calling conversation and return the final assistant text.

    The LLM chooses which tools to call and with what arguments. For each tool
    call we invoke ``run_tool(name, args)`` — supplied by the agent — and feed its
    string output back to the model, looping until the model answers with no more
    tool calls (or ``max_iters`` is hit, after which we force a final answer).

    ``run_tool`` is where the agent executes the real tool (RAG retrieval) and
    records citations; this function only orchestrates the OpenAI protocol.
    Only used when the provider is OpenAI (the agent gates this).
    """
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    with httpx.Client(timeout=120.0) as client:
        for _ in range(max_iters):
            data = _openai_post(
                client,
                {
                    "model": settings.OPENAI_CHAT_MODEL,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "temperature": temperature,
                },
            )
            msg = data["choices"][0]["message"]
            tool_calls = msg.get("tool_calls")

            if not tool_calls:
                return msg.get("content") or ""

            # Append the assistant turn verbatim (the API requires it before the
            # corresponding tool messages) and execute each requested tool.
            messages.append(msg)
            for call in tool_calls:
                fn = call.get("function", {})
                name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                try:
                    output = run_tool(name, args)
                except Exception as exc:  # one bad tool must not kill the turn
                    logger.warning("Tool '%s' raised: %s", name, exc)
                    output = f"Tool '{name}' failed: {exc}"
                messages.append(
                    {"role": "tool", "tool_call_id": call.get("id"), "content": output}
                )

        # Iterations exhausted — force a final answer with no further tools.
        data = _openai_post(
            client,
            {
                "model": settings.OPENAI_CHAT_MODEL,
                "messages": messages,
                "temperature": temperature,
            },
        )
        return data["choices"][0]["message"].get("content") or ""


# ── Ollama path ────────────────────────────────────────────────────────────────

def _ollama_completion(
    system_prompt: str,
    user_message: str,
    temperature: float,
) -> str:
    """
    POST to Ollama /api/chat and return the assistant content string.
    Raises RuntimeError on connection failure so callers can handle gracefully.
    """
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "options": {"temperature": temperature},
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{settings.OLLAMA_BASE_URL}/api/chat", json=payload)
            resp.raise_for_status()
    except httpx.ConnectError:
        raise RuntimeError(
            f"Cannot reach Ollama at {settings.OLLAMA_BASE_URL}. "
            "Is Ollama running? Or set LLM_PROVIDER=openai (or =mock) in .env."
        )
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text}")

    data = resp.json()
    return data["message"]["content"]
