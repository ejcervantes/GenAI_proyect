"""
APScheduler configuration.

Sets up a BackgroundScheduler with a single cron job that runs
run_global_refresh_job() every POLICY_REFRESH_INTERVAL_HOURS hours (daily by
default): re-scrape all sources, re-ingest what changed, and alert matching cases.

The scheduler is started in app/main.py lifespan and shut down cleanly on exit.
Each job invocation opens its own DB session and closes it when done,
so it never shares a session with the HTTP request thread pool.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def _run_job() -> None:
    """
    Wrapper called by APScheduler.
    Opens a fresh DB session for this job invocation and closes it when done.
    Importing here (not at module level) avoids circular imports at startup.
    """
    from app.db.session import SessionLocal
    from app.services.change_tracking.tracker import run_global_refresh_job

    db = SessionLocal()
    try:
        result = run_global_refresh_job(db)
        logger.info("Scheduled global RAG refresh finished: %s", result)
    except Exception as exc:
        logger.error("Scheduled global refresh raised an unhandled exception: %s", exc)
    finally:
        db.close()


def start_scheduler() -> None:
    """
    Register the cron job and start the background scheduler.
    Safe to call multiple times — will not add duplicate jobs.
    """
    if scheduler.running:
        logger.debug("Scheduler already running — skipping start")
        return

    scheduler.add_job(
        _run_job,
        trigger=IntervalTrigger(hours=settings.POLICY_REFRESH_INTERVAL_HOURS),
        id="global_rag_refresh_job",
        name="Global RAG refresh & change alerts",
        replace_existing=True,
        misfire_grace_time=300,  # 5-minute window if the job fires late
    )

    scheduler.start()
    logger.info(
        "APScheduler started — global RAG refresh will run every %d hour(s)",
        settings.POLICY_REFRESH_INTERVAL_HOURS,
    )


def stop_scheduler() -> None:
    """Gracefully stop the scheduler on application shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
