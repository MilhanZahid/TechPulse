"""APScheduler setup — reads schedule from DB and triggers the pipeline."""
import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def _run() -> None:
    from agents.orchestrator import run_pipeline
    logger.info("Scheduled pipeline run starting at %s", datetime.utcnow())
    result = await run_pipeline()
    logger.info("Scheduled pipeline run finished: %s", result)


def load_schedule_from_db() -> None:
    """Read schedule_config from DB and (re)register jobs."""
    from db.connection import SessionLocal
    from db.models import ScheduleConfig

    db = SessionLocal()
    try:
        config = db.query(ScheduleConfig).first()
    finally:
        db.close()

    scheduler.remove_all_jobs()

    if not config or not config.is_active or not config.refresh_times:
        logger.info("Scheduler: no active schedule configured")
        return

    tz = config.timezone or "UTC"
    for time_str in config.refresh_times:
        try:
            hour, minute = time_str.split(":")
            scheduler.add_job(
                _run,
                CronTrigger(hour=int(hour), minute=int(minute), timezone=tz),
                id=f"pipeline_{time_str}",
                replace_existing=True,
            )
            logger.info("Scheduled pipeline at %s (%s)", time_str, tz)
        except Exception as exc:
            logger.warning("Bad schedule time '%s': %s", time_str, exc)


def start_scheduler() -> None:
    load_schedule_from_db()
    scheduler.start()
    logger.info("APScheduler started")
