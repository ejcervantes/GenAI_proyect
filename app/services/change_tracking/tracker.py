"""
Change tracking.

Two entry points:

run_global_refresh_job(db)  — the DAILY scheduled job. Scrapes the entire source
  corpus, groups by (nationality, destination, purpose) triple, and for each
  triple diffs the freshly-scraped text against yesterday's snapshot. ONLY when
  the text changed does it: (a) re-ingest that triple into the RAG, and (b) raise
  a ChangeAlert (with an LLM summary) for every tracked VisaCase matching the
  triple. No change → no re-ingest, no alert. This keeps the knowledge base fresh
  for all users and alerts only those who care, only when something actually moved.

check_case(visa_case, db)  — unit of work for a single VisaCase, used by the
  manual "check my cases now" endpoint. Same scrape → diff → (summarise, alert,
  re-ingest) → snapshot flow, scoped to one case's triple.

Both share the same per-triple snapshot files, so whichever runs first advances
the snapshot and the other sees no diff — that is the de-duplication mechanism.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.change_alert import ChangeAlert
from app.models.visa_case import VisaCase
from app.services.change_tracking.differ import DiffResult, compute_diff
from app.services.change_tracking.snapshot_store import load_snapshot, save_snapshot
from app.services.change_tracking.summariser import summarise_change
from app.services.rag.ingestion import ingest_all, ingest_policies
from app.services.scraper import get_visa_policies

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Global daily refresh
# ══════════════════════════════════════════════════════════════════════════════


def run_global_refresh_job(db: Session) -> dict:
    """
    Daily entry point invoked by APScheduler. Returns a summary dict for logging.
    """
    policies = get_visa_policies()  # whole corpus; live-fetched if SCRAPER_MOCK=false
    groups = _group_by_triple(policies)

    triples_checked = 0
    triples_changed = 0
    alerts_created = 0
    errors = 0

    logger.info("Global RAG refresh started: %d source group(s) to check", len(groups))

    for (nationality, destination, purpose), docs in groups.items():
        triples_checked += 1
        try:
            changed, n_alerts = _refresh_triple(db, nationality, destination, purpose, docs)
            if changed:
                triples_changed += 1
                alerts_created += n_alerts
        except Exception as exc:
            logger.error(
                "Global refresh error for %s→%s (%s): %s",
                nationality, destination, purpose, exc,
            )
            errors += 1

    db.commit()

    result = {
        "triples_checked": triples_checked,
        "triples_changed": triples_changed,
        "alerts_created": alerts_created,
        "errors": errors,
    }
    logger.info("Global RAG refresh complete: %s", result)
    return result


def _group_by_triple(policies: list[dict]) -> dict[tuple[str, str, str], list[dict]]:
    """Group scraped docs by their (nationality, destination, purpose) triple."""
    groups: dict[tuple[str, str, str], list[dict]] = {}
    for p in policies:
        key = (
            p["passport_nationality"],
            p["destination_country"],
            p["travel_purpose"],
        )
        groups.setdefault(key, []).append(p)
    return groups


def _refresh_triple(
    db: Session,
    nationality: str,
    destination: str,
    purpose: str,
    docs: list[dict],
) -> tuple[bool, int]:
    """
    Diff this triple's freshly-scraped text against its snapshot. Returns
    (changed, alerts_created). On change: re-ingest the SAME docs (no re-fetch),
    save the new snapshot, and alert every tracked VisaCase matching the triple.
    """
    new_text = "\n\n".join(d["content"] for d in docs)
    source_url = docs[0].get("source", "") if docs else ""

    old_text = load_snapshot(nationality, destination, purpose)

    # First time we see this triple — store the baseline, nothing to diff yet.
    if old_text is None:
        save_snapshot(nationality, destination, purpose, new_text)
        return (False, 0)

    diff = compute_diff(old_text, new_text)
    if not diff.has_changes:
        return (False, 0)

    logger.info(
        "Change detected %s→%s (%s): type=%s severity=%s",
        nationality, destination, purpose, diff.change_type, diff.severity,
    )

    summary, action_required = summarise_change(
        diff=diff,
        passport_nationality=nationality,
        destination_country=destination,
        travel_purpose=purpose,
    )

    # Re-ingest the very text we diffed (no second fetch).
    try:
        n = ingest_policies(docs)
        logger.info("Re-ingested %d chunks for %s→%s (%s)", n, nationality, destination, purpose)
    except Exception as exc:
        logger.warning(
            "Re-ingestion failed for %s→%s (%s): %s (non-fatal)",
            nationality, destination, purpose, exc,
        )

    save_snapshot(nationality, destination, purpose, new_text)

    n_alerts = _alert_matching_cases(
        db, nationality, destination, purpose, source_url, diff, summary, action_required
    )
    return (True, n_alerts)


def _alert_matching_cases(
    db: Session,
    nationality: str,
    destination: str,
    purpose: str,
    source_url: str,
    diff: DiffResult,
    summary: str,
    action_required,
) -> int:
    """
    Create a ChangeAlert for every tracked VisaCase whose triple matches the
    changed source. Matching is case-insensitive. Returns the number created.
    """
    cases = (
        db.query(VisaCase)
        .filter(
            VisaCase.is_tracking == True,  # noqa: E712
            func.lower(VisaCase.passport_nationality) == nationality.lower(),
            func.lower(VisaCase.destination_country) == destination.lower(),
            func.lower(VisaCase.travel_purpose) == purpose.lower(),
        )
        .all()
    )

    now = datetime.now(timezone.utc)
    for case in cases:
        db.add(
            ChangeAlert(
                visa_case_id=case.id,
                source_url=source_url,
                change_type=diff.change_type,
                summary=summary,
                raw_diff=diff.raw_diff,
                action_required=action_required,
                severity=diff.severity,
                is_read=False,
            )
        )
        case.last_checked_at = now

    if cases:
        logger.info(
            "Created %d alert(s) for %s→%s (%s)",
            len(cases), nationality, destination, purpose,
        )
    return len(cases)


def run_change_tracking_job(db: Session) -> dict:
    """
    Entry point for the APScheduler cron job.
    Checks all VisaCases with is_tracking=True.
    Returns a summary dict with counts for logging/monitoring.
    """
    cases = (
        db.query(VisaCase)
        .filter(VisaCase.is_tracking == True)  # noqa: E712
        .all()
    )

    total = len(cases)
    changed = 0
    errors = 0

    logger.info("Change tracking job started: %d cases to check", total)

    for case in cases:
        try:
            alert_created = check_case(case, db)
            if alert_created:
                changed += 1
        except Exception as exc:
            logger.error(
                "Error checking case #%d (%s→%s): %s",
                case.id, case.passport_nationality, case.destination_country, exc,
            )
            errors += 1

    logger.info(
        "Change tracking job complete: %d checked, %d changes found, %d errors",
        total, changed, errors,
    )
    return {"total": total, "changed": changed, "errors": errors}


def check_case(visa_case: VisaCase, db: Session) -> bool:
    """
    Check one VisaCase for policy changes.
    Returns True if a ChangeAlert was created, False otherwise.
    """
    nationality = visa_case.passport_nationality
    destination = visa_case.destination_country
    purpose = visa_case.travel_purpose

    # 1. Scrape fresh policy text
    policies = get_visa_policies(
        passport_nationality=nationality,
        destination_country=destination,
        travel_purpose=purpose,
    )

    if not policies:
        logger.debug("No policies found for case #%d — skipping", visa_case.id)
        _stamp_checked(visa_case, db)
        return False

    # Concatenate all matched policy texts into one comparable string
    new_text = "\n\n".join(p["content"] for p in policies)
    source_url = policies[0].get("source", "") if policies else ""

    # 2. Load previous snapshot
    old_text = load_snapshot(nationality, destination, purpose)

    # First run — no snapshot yet; just save and move on
    if old_text is None:
        save_snapshot(nationality, destination, purpose, new_text)
        _stamp_checked(visa_case, db)
        logger.debug("Case #%d: first snapshot saved, no diff possible yet", visa_case.id)
        return False

    # 3. Diff
    diff = compute_diff(old_text, new_text)

    if not diff.has_changes:
        _stamp_checked(visa_case, db)
        logger.debug("Case #%d: no changes detected", visa_case.id)
        return False

    logger.info(
        "Case #%d (%s→%s, %s): change detected — type=%s severity=%s",
        visa_case.id, nationality, destination, purpose,
        diff.change_type, diff.severity,
    )

    # 4. Summarise via LLM
    summary, action_required = summarise_change(
        diff=diff,
        passport_nationality=nationality,
        destination_country=destination,
        travel_purpose=purpose,
    )

    # 5. Create ChangeAlert
    alert = ChangeAlert(
        visa_case_id=visa_case.id,
        source_url=source_url,
        change_type=diff.change_type,
        summary=summary,
        raw_diff=diff.raw_diff,
        action_required=action_required,
        severity=diff.severity,
        is_read=False,
    )
    db.add(alert)

    # 6. Re-ingest updated policy into ChromaDB
    try:
        n = ingest_all(
            passport_nationality=nationality,
            destination_country=destination,
            travel_purpose=purpose,
        )
        logger.info("Re-ingested %d chunks for case #%d after policy change", n, visa_case.id)
    except Exception as exc:
        logger.warning("Re-ingestion failed for case #%d: %s (non-fatal)", visa_case.id, exc)

    # 7. Save new snapshot and stamp the case
    save_snapshot(nationality, destination, purpose, new_text)
    _stamp_checked(visa_case, db)

    db.commit()
    return True


def _stamp_checked(visa_case: VisaCase, db: Session) -> None:
    """Update last_checked_at without triggering a full refresh."""
    visa_case.last_checked_at = datetime.now(timezone.utc)
    db.add(visa_case)
