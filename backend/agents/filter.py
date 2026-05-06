"""
Filter Agent — cleans up raw scraped articles before clustering.

Two passes:
1. URL normalization dedup — same URL with tracking params → same article
2. Title similarity dedup — same story covered twice by same source → keep higher tier
3. Relevance scoring — keyword density × tier weight × content quality
"""
import logging
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from db.models import Article

logger = logging.getLogger(__name__)

TECH_KEYWORDS = {
    "ai", "machine learning", "llm", "gpt", "model", "openai", "google", "microsoft",
    "nvidia", "chip", "gpu", "open source", "developer", "api", "cloud", "startup",
    "funding", "launch", "release", "research", "paper", "benchmark", "agent",
    "transformer", "diffusion", "robotics", "hardware", "software", "security",
    "privacy", "regulation", "acquisition", "ipo", "product", "feature", "anthropic",
    "gemini", "claude", "copilot", "cursor", "github", "aws", "azure", "apple",
    "meta", "samsung", "quantum", "autonomous", "inference", "fine-tuning", "rag",
}

# URL query params that are pure tracking noise
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "referrer", "source", "via", "mc_cid", "mc_eid", "fbclid",
    "gclid", "msclkid", "trk", "linkId",
}

TIER_WEIGHTS = {1: 1.0, 2: 0.85, 3: 0.9, 4: 0.7, 5: 0.95}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_url(url: str) -> str:
    """Strip tracking query params and normalize scheme+host to lowercase."""
    try:
        parsed = urlparse(url.strip())
        qs = parse_qs(parsed.query, keep_blank_values=False)
        clean_qs = {k: v for k, v in qs.items() if k.lower() not in _TRACKING_PARAMS}
        clean = parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=parsed.netloc.lower().lstrip("www."),
            query=urlencode(clean_qs, doseq=True),
            fragment="",
        )
        return urlunparse(clean).rstrip("/")
    except Exception:
        return url.strip()


def _title_tokens(title: str) -> set[str]:
    """Lowercase word tokens, strip punctuation, drop stop words."""
    STOP = {"the", "a", "an", "of", "in", "to", "for", "and", "is", "on",
            "at", "by", "with", "its", "as", "be", "that", "this", "are"}
    words = re.findall(r"[a-z0-9]+", title.lower())
    return {w for w in words if w not in STOP and len(w) > 2}


def _title_jaccard(a: str, b: str) -> float:
    ta, tb = _title_tokens(a), _title_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _content_quality(article: Article) -> float:
    """0–1 score based on content length and structure signals."""
    content = article.raw_content or ""
    length_score = min(len(content) / 2000, 1.0)
    has_paragraphs = 0.2 if "\n" in content else 0.0
    return length_score * 0.8 + has_paragraphs


def score_article(article: Article) -> float:
    text = ((article.title or "") + " " + (article.raw_content or "")).lower()
    keyword_hits = sum(1 for kw in TECH_KEYWORDS if kw in text)
    keyword_score = min(keyword_hits / 6.0, 1.0)
    tier_weight = TIER_WEIGHTS.get(article.source_tier, 0.5)
    quality = _content_quality(article)
    return round((keyword_score * 0.7 + quality * 0.3) * tier_weight * 10, 2)


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def run_filter(article_ids: list[int], db) -> list[int]:
    """
    Score + deduplicate articles.
    Returns IDs of articles that passed the relevance threshold,
    with near-duplicate titles (same source, Jaccard ≥ 0.75) removed.
    """
    MIN_SCORE = 1.5
    articles = db.query(Article).filter(Article.id.in_(article_ids)).all()

    # Pass 1: score all
    for article in articles:
        article.relevance_score = score_article(article)
    db.commit()

    # Pass 2: URL-normalized dedup against already-stored articles
    norm_url_map: dict[str, int] = {}
    scored_passing: list[Article] = []
    for a in sorted(articles, key=lambda x: x.source_tier):
        if a.relevance_score < MIN_SCORE:
            continue
        norm = _normalize_url(a.url)
        if norm in norm_url_map:
            logger.debug("URL dedup drop: %s", a.url)
            continue
        norm_url_map[norm] = a.id
        scored_passing.append(a)

    # Pass 3: title similarity dedup (within same source tier)
    final: list[Article] = []
    for a in scored_passing:
        duplicate = False
        for b in final:
            if _title_jaccard(a.title or "", b.title or "") >= 0.75:
                # Keep the one from the higher tier (lower tier number)
                if a.source_tier < b.source_tier:
                    final.remove(b)
                    break
                duplicate = True
                break
        if not duplicate:
            final.append(a)

    passing_ids = [a.id for a in final]
    logger.info(
        "Filter: %d → scored %d → deduped to %d articles",
        len(article_ids), len(scored_passing), len(passing_ids),
    )
    return passing_ids
