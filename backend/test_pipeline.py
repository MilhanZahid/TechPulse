"""
Standalone pipeline test script.
Run from backend/ directory after setting up .env:

    python test_pipeline.py [stage]

Stages:
    scraper   — run just the scraper, print article count
    filter    — run scraper + filter, print pass rate
    cluster   — run scraper + filter + cluster, print story clusters
    brief     — full pipeline (all stages including Brief Agent)
    full      — alias for brief
    db        — just verify DB connection and print table counts

Example:
    python test_pipeline.py scraper
    python test_pipeline.py full
"""
import asyncio
import logging
import sys
import os

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("test_pipeline")


def _check_env() -> bool:
    missing = [v for v in ["GROQ_API_KEY", "DATABASE_URL"] if not os.getenv(v)]
    if missing:
        print(f"[ERROR] Missing env vars: {', '.join(missing)}")
        print("Copy backend/.env.example to backend/.env and fill in values.")
        return False
    return True


# ---------------------------------------------------------------------------
# DB test
# ---------------------------------------------------------------------------

def test_db() -> None:
    from db.connection import engine, init_db
    from db.models import Article, Story, Trend, PipelineRun
    from sqlalchemy import text

    print("\n=== DB Connection Test ===")
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✓ Connected to PostgreSQL")

    init_db()
    print("✓ Tables created / verified")

    from db.connection import SessionLocal
    db = SessionLocal()
    try:
        print(f"  Articles:  {db.query(Article).count()}")
        print(f"  Stories:   {db.query(Story).count()}")
        print(f"  Trends:    {db.query(Trend).count()}")
        print(f"  Runs:      {db.query(PipelineRun).count()}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Scraper test
# ---------------------------------------------------------------------------

async def test_scraper() -> list:
    from agents.scraper import run_scraper

    print("\n=== Scraper Test ===")
    print("Scraping RSS feeds and APIs (Crawl4AI sources may be slow)...")
    articles = await run_scraper()
    print(f"✓ Collected {len(articles)} unique articles")

    by_source: dict[str, int] = {}
    for a in articles:
        by_source[a["source_name"]] = by_source.get(a["source_name"], 0) + 1
    for src, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"   {src}: {count}")
    return articles


# ---------------------------------------------------------------------------
# Filter test
# ---------------------------------------------------------------------------

def test_filter(article_ids: list[int], db) -> list[int]:
    from agents.filter import run_filter

    print("\n=== Filter Test ===")
    passing = run_filter(article_ids, db)
    pct = len(passing) / len(article_ids) * 100 if article_ids else 0
    print(f"✓ {len(passing)}/{len(article_ids)} articles passed ({pct:.0f}%)")
    return passing


# ---------------------------------------------------------------------------
# Cluster test
# ---------------------------------------------------------------------------

def test_cluster(passing_ids: list[int], db) -> list[int]:
    from agents.cluster import run_cluster
    from db.models import Story

    print("\n=== Cluster Test ===")
    print(f"Clustering {len(passing_ids)} articles with Claude...")
    story_ids = run_cluster(passing_ids, db)
    print(f"✓ Created {len(story_ids)} story clusters")

    for sid in story_ids[:10]:
        s = db.query(Story).filter(Story.id == sid).first()
        if s:
            print(f"   [{s.category}] {s.headline} ({s.source_count} sources)")
    if len(story_ids) > 10:
        print(f"   ... and {len(story_ids) - 10} more")
    return story_ids


# ---------------------------------------------------------------------------
# Brief test
# ---------------------------------------------------------------------------

def test_brief(story_ids: list[int], db) -> None:
    from agents.brief import run_brief
    from db.models import Story

    print("\n=== Brief Agent Test ===")
    print("Writing summaries with Claude...")
    run_brief(story_ids, db)

    for sid in story_ids[:5]:
        s = db.query(Story).filter(Story.id == sid).first()
        if s:
            print(f"\n  [{s.category}] importance={s.importance_score}")
            print(f"  Headline: {s.headline}")
            print(f"  Summary:  {s.summary}")
    print("\n✓ Brief agent done")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(stage: str) -> None:
    if not _check_env():
        sys.exit(1)

    from db.connection import init_db, SessionLocal
    init_db()

    if stage == "db":
        test_db()
        return

    db = SessionLocal()
    try:
        from agents.scraper import persist_articles

        if stage in ("scraper",):
            await test_scraper()
            return

        articles = await test_scraper()
        new_ids = persist_articles(articles, db)
        print(f"\n✓ Persisted {len(new_ids)} new articles to DB")

        if stage == "scraper":
            return

        passing_ids = test_filter(new_ids, db)

        if stage == "filter":
            return

        if not passing_ids:
            print("[WARN] No articles passed filter — nothing to cluster.")
            return

        story_ids = test_cluster(passing_ids, db)

        if stage == "cluster":
            return

        if story_ids:
            test_brief(story_ids, db)

    finally:
        db.close()


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "full"
    valid = {"db", "scraper", "filter", "cluster", "brief", "full"}
    if stage not in valid:
        print(f"Unknown stage '{stage}'. Choose from: {', '.join(sorted(valid))}")
        sys.exit(1)
    asyncio.run(main(stage))
