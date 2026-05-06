"""
Orchestrator — manages the full pipeline:
  Scraper → Filter → Cluster → Brief

Each stage is run in sequence. If a stage fails, it logs the error and
aborts the run gracefully without crashing the process.
"""
import logging
from datetime import datetime

from db.connection import SessionLocal
from db.models import PipelineRun

logger = logging.getLogger(__name__)


async def run_pipeline() -> dict:
    """Execute the full scrape + process pipeline. Returns a run summary dict."""
    db = SessionLocal()
    run = PipelineRun(started_at=datetime.utcnow(), status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    result = {
        "run_id": run.id,
        "articles_scraped": 0,
        "stories_processed": 0,
        "status": "failed",
        "error": None,
    }

    try:
        # Stage 1: Scrape
        logger.info("Pipeline [run %d]: starting scraper", run.id)
        from agents.scraper import run_scraper, persist_articles
        raw_articles = await run_scraper()
        new_ids = persist_articles(raw_articles, db)
        result["articles_scraped"] = len(new_ids)
        logger.info("Pipeline [run %d]: scraped %d new articles", run.id, len(new_ids))

        if not new_ids:
            logger.info("Pipeline [run %d]: no new articles, skipping downstream stages", run.id)
            result["status"] = "completed"
            _finalize_run(run, result, db)
            return result

        # Stage 2: Filter
        logger.info("Pipeline [run %d]: running filter", run.id)
        from agents.filter import run_filter
        passing_ids = run_filter(new_ids, db)
        logger.info("Pipeline [run %d]: %d articles passed filter", run.id, len(passing_ids))

        if not passing_ids:
            result["status"] = "completed"
            _finalize_run(run, result, db)
            return result

        # Stage 3: Cluster
        logger.info("Pipeline [run %d]: running cluster", run.id)
        from agents.cluster import run_cluster
        story_ids = run_cluster(passing_ids, db)
        result["stories_processed"] = len(story_ids)
        logger.info("Pipeline [run %d]: clustered into %d stories", run.id, len(story_ids))

        # Stage 4: Brief
        logger.info("Pipeline [run %d]: running brief agent", run.id)
        from agents.brief import run_brief
        run_brief(story_ids, db)

        result["status"] = "completed"

    except Exception as exc:
        logger.exception("Pipeline [run %d] failed: %s", run.id, exc)
        result["error"] = str(exc)
        result["status"] = "failed"

    finally:
        _finalize_run(run, result, db)
        db.close()

    return result


def _finalize_run(run: PipelineRun, result: dict, db) -> None:
    run.finished_at = datetime.utcnow()
    run.articles_scraped = result["articles_scraped"]
    run.stories_processed = result["stories_processed"]
    run.status = result["status"]
    run.error_log = result.get("error")
    db.commit()
