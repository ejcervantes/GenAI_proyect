"""
Visa policy scraper — official Pakistan → Germany sources.

The seed corpus (mock_data.py) defines WHICH official pages to track: each entry
carries the real source URL plus a trusted fallback text. This scraper drives the
daily refresh:

  SCRAPER_MOCK=true  → return the seed text only (no network calls). Good for dev
                       and CI; the snapshot/diff job then sees stable text.
  SCRAPER_MOCK=false → for each matching source, fetch the live page, extract its
                       main text, and return that. If a fetch fails or the page
                       yields too little usable text, fall back to the seed text
                       for that source so the RAG is never left empty.

Either way the output schema is identical, so ingestion and change-tracking are
agnostic to whether the text came from the network or the seed.

The change-tracking job compares this output against yesterday's snapshot and
only re-ingests when the text actually changed.
"""

import logging
from datetime import date
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.services.scraper.mock_data import MOCK_VISA_POLICIES

logger = logging.getLogger(__name__)

# A live fetch must yield at least this many characters of extracted text to be
# trusted; anything shorter is treated as a failed/blocked fetch and we fall back.
_MIN_LIVE_CHARS = 400
_FETCH_TIMEOUT = 15.0
_USER_AGENT = (
    "PassportAI/0.1 (+https://example.com/passportai; visa guidance assistant)"
)


def get_visa_policies(
    passport_nationality: Optional[str] = None,
    destination_country: Optional[str] = None,
    travel_purpose: Optional[str] = None,
) -> list[dict]:
    """
    Return visa policy documents, optionally filtered by metadata.
    Each dict has keys: source, passport_nationality, destination_country,
    travel_purpose, title, content, last_scraped.
    """
    sources = _filter(
        MOCK_VISA_POLICIES, passport_nationality, destination_country, travel_purpose
    )

    if settings.SCRAPER_MOCK:
        logger.debug("Scraper: SCRAPER_MOCK=true — returning %d seed docs", len(sources))
        return [dict(s) for s in sources]

    logger.info("Scraper: live fetch for %d source(s)", len(sources))
    return [_fetch_or_fallback(s) for s in sources]


# ── Filtering ──────────────────────────────────────────────────────────────────


def _filter(
    policies: list[dict],
    passport_nationality: Optional[str],
    destination_country: Optional[str],
    travel_purpose: Optional[str],
) -> list[dict]:
    results = []
    for p in policies:
        if passport_nationality and p["passport_nationality"].lower() not in (
            passport_nationality.lower(),
            "general",
        ):
            continue
        if (
            destination_country
            and p["destination_country"].lower() != destination_country.lower()
        ):
            continue
        if travel_purpose and p["travel_purpose"].lower() not in (
            travel_purpose.lower(),
            "general",
        ):
            continue
        results.append(p)
    return results


# ── Live fetch with seed fallback ───────────────────────────────────────────────


def _fetch_or_fallback(source: dict) -> dict:
    """
    Try to fetch live text for *source*; on any failure or thin content, return
    the seed entry unchanged. The returned dict always keeps the source's
    metadata (passport/destination/purpose/title); only content + last_scraped
    are refreshed on a successful fetch.
    """
    url = source["source"]
    text = _fetch_main_text(url)

    if text and len(text) >= _MIN_LIVE_CHARS:
        refreshed = dict(source)
        refreshed["content"] = text
        refreshed["last_scraped"] = _today()
        logger.info("Live fetch OK (%d chars): %s", len(text), url)
        return refreshed

    logger.warning("Live fetch unusable for %s — using seed fallback", url)
    return dict(source)


def _fetch_main_text(url: str) -> Optional[str]:
    """
    Fetch *url* and extract readable body text. Returns None on any error.
    Strips script/style/nav/footer noise and collapses whitespace.
    """
    try:
        with httpx.Client(
            timeout=_FETCH_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("HTTP error fetching %s: %s", url, exc)
        return None

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as exc:  # malformed markup — don't let it kill the job
        logger.warning("Parse error for %s: %s", url, exc)
        return None

    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.body or soup
    paragraphs = [
        p.get_text(" ", strip=True)
        for p in main.find_all(["p", "li"])
        if p.get_text(strip=True)
    ]
    text = " ".join(paragraphs)
    return text or None


def _today() -> str:
    return date.today().isoformat()
