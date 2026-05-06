"""
Scraper Agent — fetches raw articles from Tier 1, 2, and 4 sources.
Uses feedparser for RSS feeds, httpx for JSON APIs (HN, Reddit),
and Crawl4AI for JS-heavy web pages.
Each source is scraped concurrently. Failures are logged but never
crash the full run.
"""
import asyncio
import logging
import hashlib
from datetime import datetime, timedelta, timezone
from typing import TypedDict

import feedparser
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from sources.config import SourceConfig, TIER1_SOURCES, TIER2_SOURCES, TIER4_SOURCES

logger = logging.getLogger(__name__)

MAX_AGE_HOURS = 48


def _extract_markdown(result) -> str:
    """Safely extract markdown text from a Crawl4AI result object.
    In v0.4.x result.markdown may be a MarkdownGenerationResult object."""
    md = getattr(result, "markdown", None)
    if md is None:
        return ""
    if isinstance(md, str):
        return md
    # MarkdownGenerationResult — prefer fit_markdown (cleaned), fall back to raw
    for attr in ("fit_markdown", "raw_markdown", "markdown"):
        val = getattr(md, attr, None)
        if val and isinstance(val, str):
            return val
    return str(md)


class RawArticle(TypedDict):
    title: str
    url: str
    source_name: str
    source_tier: int
    raw_content: str
    scraped_at: str


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _is_recent(date_str: str | None) -> bool:
    if not date_str:
        return True
    try:
        import email.utils
        ts = email.utils.parsedate_to_datetime(date_str)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)
        return ts >= cutoff
    except Exception:
        return True


# ---------------------------------------------------------------------------
# RSS scraping
# ---------------------------------------------------------------------------

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
async def _scrape_rss(source: SourceConfig) -> list[RawArticle]:
    articles: list[RawArticle] = []
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(source.rss_url, follow_redirects=True)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)

        for entry in feed.entries[:30]:
            pub = entry.get("published") or entry.get("updated")
            if not _is_recent(pub):
                continue

            content = (
                entry.get("summary")
                or entry.get("content", [{}])[0].get("value", "")
                or entry.get("description", "")
            )
            articles.append(RawArticle(
                title=entry.get("title", "").strip(),
                url=entry.get("link", "").strip(),
                source_name=source.name,
                source_tier=source.tier,
                raw_content=content,
                scraped_at=datetime.utcnow().isoformat(),
            ))
    except Exception as exc:
        logger.warning("RSS scrape failed for %s: %s", source.name, exc)
    return articles


# ---------------------------------------------------------------------------
# Web scraping (Crawl4AI)
# ---------------------------------------------------------------------------

async def _scrape_web(source: SourceConfig) -> list[RawArticle]:
    articles: list[RawArticle] = []
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

        browser_cfg = BrowserConfig(headless=True, verbose=False)
        run_cfg = CrawlerRunConfig(word_count_threshold=50)

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=source.url, config=run_cfg)

        if not result.success:
            logger.warning("Crawl4AI failed for %s", source.name)
            return articles

        # Extract links from markdown/html
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(result.html or "", "lxml")
        selector = source.selectors.get("article_links", "a")
        links = [
            a.get("href", "") for a in soup.select(selector)
            if a.get("href")
        ]

        # Deduplicate and resolve relative URLs
        seen: set[str] = set()
        base = source.url.rstrip("/")
        resolved: list[str] = []
        for href in links:
            href = href.strip()
            if not href.startswith("http"):
                href = base + "/" + href.lstrip("/")
            if href not in seen:
                seen.add(href)
                resolved.append(href)

        # Scrape up to 10 individual article pages
        async def _fetch_article(url: str) -> RawArticle | None:
            try:
                async with AsyncWebCrawler(config=browser_cfg) as c:
                    r = await c.arun(url=url, config=run_cfg)
                if not r.success:
                    return None
                md = _extract_markdown(r)
                if not md:
                    return None
                title = r.metadata.get("title", url) if r.metadata else url
                return RawArticle(
                    title=title.strip(),
                    url=url,
                    source_name=source.name,
                    source_tier=source.tier,
                    raw_content=md[:8000],
                    scraped_at=datetime.utcnow().isoformat(),
                )
            except Exception as exc:
                logger.debug("Article fetch failed %s: %s", url, exc)
                return None

        tasks = [_fetch_article(u) for u in resolved[:10]]
        results = await asyncio.gather(*tasks)
        articles = [a for a in results if a is not None]

    except Exception as exc:
        logger.warning("Web scrape failed for %s: %s", source.name, exc)
    return articles


# ---------------------------------------------------------------------------
# HN API
# ---------------------------------------------------------------------------

async def _scrape_hackernews() -> list[RawArticle]:
    articles: list[RawArticle] = []
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
            resp.raise_for_status()
            ids = resp.json()[:30]

            async def _fetch_item(item_id: int) -> RawArticle | None:
                try:
                    r = await client.get(
                        f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
                    )
                    data = r.json()
                    if not data or data.get("type") != "story":
                        return None
                    url = data.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
                    return RawArticle(
                        title=data.get("title", "").strip(),
                        url=url,
                        source_name="Hacker News",
                        source_tier=4,
                        raw_content=data.get("text", "") or "",
                        scraped_at=datetime.utcnow().isoformat(),
                    )
                except Exception:
                    return None

            tasks = [_fetch_item(i) for i in ids]
            results = await asyncio.gather(*tasks)
            articles = [a for a in results if a is not None]
    except Exception as exc:
        logger.warning("HN scrape failed: %s", exc)
    return articles


# ---------------------------------------------------------------------------
# Reddit JSON API
# ---------------------------------------------------------------------------

async def _scrape_reddit(source: SourceConfig) -> list[RawArticle]:
    articles: list[RawArticle] = []
    try:
        headers = {"User-Agent": "TechPulse/1.0 (personal dashboard)"}
        async with httpx.AsyncClient(timeout=20, headers=headers) as client:
            resp = await client.get(source.url)
            resp.raise_for_status()
            data = resp.json()

        for post in data.get("data", {}).get("children", [])[:20]:
            p = post.get("data", {})
            if p.get("is_self"):
                content = p.get("selftext", "")
            else:
                content = p.get("url", "")
            articles.append(RawArticle(
                title=p.get("title", "").strip(),
                url="https://reddit.com" + p.get("permalink", ""),
                source_name=source.name,
                source_tier=source.tier,
                raw_content=content,
                scraped_at=datetime.utcnow().isoformat(),
            ))
    except Exception as exc:
        logger.warning("Reddit scrape failed for %s: %s", source.name, exc)
    return articles


# ---------------------------------------------------------------------------
# Product Hunt (web)
# ---------------------------------------------------------------------------

async def _scrape_product_hunt() -> list[RawArticle]:
    source = next(s for s in TIER4_SOURCES if s.name == "Product Hunt")
    articles: list[RawArticle] = []
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        from bs4 import BeautifulSoup

        browser_cfg = BrowserConfig(headless=True, verbose=False)
        run_cfg = CrawlerRunConfig(word_count_threshold=20)

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=source.url, config=run_cfg)

        if not result.success:
            return articles

        soup = BeautifulSoup(result.html or "", "lxml")
        for item in soup.select("a[href*='/posts/']")[:20]:
            href = item.get("href", "")
            if not href.startswith("http"):
                href = "https://www.producthunt.com" + href
            title = item.get_text(strip=True)
            if title:
                articles.append(RawArticle(
                    title=title,
                    url=href,
                    source_name="Product Hunt",
                    source_tier=4,
                    raw_content="",
                    scraped_at=datetime.utcnow().isoformat(),
                ))
    except Exception as exc:
        logger.warning("Product Hunt scrape failed: %s", exc)
    return articles


# ---------------------------------------------------------------------------
# Main entry: scrape all tiers in parallel
# ---------------------------------------------------------------------------

async def run_scraper() -> list[RawArticle]:
    """Scrape all configured sources concurrently. Returns deduplicated articles."""
    tasks: list[asyncio.Task] = []

    for source in TIER1_SOURCES + TIER2_SOURCES:
        if source.scrape_type == "rss":
            tasks.append(asyncio.create_task(_scrape_rss(source)))
        else:
            tasks.append(asyncio.create_task(_scrape_web(source)))

    for source in TIER4_SOURCES:
        if source.name == "Hacker News":
            tasks.append(asyncio.create_task(_scrape_hackernews()))
        elif source.name == "Product Hunt":
            tasks.append(asyncio.create_task(_scrape_product_hunt()))
        elif "reddit.com" in source.url:
            tasks.append(asyncio.create_task(_scrape_reddit(source)))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_articles: list[RawArticle] = []
    seen_urls: set[str] = set()
    for r in results:
        if isinstance(r, Exception):
            logger.error("Scraper task raised: %s", r)
            continue
        for article in r:
            if article["url"] and article["url"] not in seen_urls:
                seen_urls.add(article["url"])
                all_articles.append(article)

    logger.info("Scraper collected %d unique articles", len(all_articles))
    return all_articles


# ---------------------------------------------------------------------------
# DB persistence helper (called by orchestrator)
# ---------------------------------------------------------------------------

def persist_articles(articles: list[RawArticle], db) -> list[int]:
    """Insert new articles into DB, skip duplicates. Returns list of new IDs."""
    from db.models import Article

    new_ids: list[int] = []
    for a in articles:
        if not a["title"] or not a["url"]:
            continue
        existing = db.query(Article).filter(Article.url == a["url"]).first()
        if existing:
            continue
        row = Article(
            title=a["title"],
            url=a["url"],
            source_name=a["source_name"],
            source_tier=a["source_tier"],
            raw_content=a["raw_content"],
            scraped_at=datetime.utcnow(),
        )
        db.add(row)
        db.flush()
        new_ids.append(row.id)

    db.commit()
    logger.info("Persisted %d new articles to DB", len(new_ids))
    return new_ids
