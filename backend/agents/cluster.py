"""
Cluster Agent — groups related articles into story clusters using Claude.

Claude receives batches of article titles and returns a JSON clustering:
which articles cover the same event, what category each cluster belongs to,
and a clean headline. Falls back to keyword-based clustering if the API call
fails so the pipeline always completes.

Trend detection: compares today's category counts against the rolling history
in the trends table and updates momentum scores.
"""
import json
import logging
import os
import uuid
from collections import defaultdict
from datetime import datetime, timedelta

from groq import Groq

from db.models import Article, Story, StorySource, Trend

logger = logging.getLogger(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

VALID_CATEGORIES = [
    "AI & Models",
    "Chips & Hardware",
    "Dev Tools",
    "Web & Infrastructure",
    "Tech Business",
    "Security & Privacy",
    "Consumer Tech",
]

CLUSTER_PROMPT = """\
You are analyzing a list of tech news article titles to group them into story clusters.

Rules:
- Articles covering the SAME specific event or announcement → same cluster
- Articles about the same general topic but different events → different clusters
- Every article must appear in exactly one cluster
- Each cluster gets one of these categories: {categories}
- Pick the most specific category that fits

Articles (format: ID: title):
{articles}

Respond with ONLY valid JSON, no markdown, no explanation:
{{
  "clusters": [
    {{
      "article_ids": [<list of integer IDs>],
      "category": "<category from the list>",
      "headline": "<clean 10-word-max headline for this cluster>"
    }}
  ]
}}"""


# ---------------------------------------------------------------------------
# Claude clustering
# ---------------------------------------------------------------------------

def _cluster_with_claude(articles: list[Article]) -> list[dict] | None:
    """Send titles to Claude, get back cluster assignments. Returns None on failure."""
    article_lines = "\n".join(f"{a.id}: {a.title}" for a in articles)
    prompt = CLUSTER_PROMPT.format(
        categories=", ".join(VALID_CATEGORIES),
        articles=article_lines,
    )
    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        clusters = data.get("clusters", [])
        # Validate structure
        for c in clusters:
            if not isinstance(c.get("article_ids"), list):
                return None
            if c.get("category") not in VALID_CATEGORIES:
                c["category"] = "Tech Business"
        return clusters
    except Exception as exc:
        logger.warning("Claude clustering failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Fallback: keyword-based clustering
# ---------------------------------------------------------------------------

_KEYWORD_SETS: dict[str, set[str]] = {
    "AI & Models": {"ai", "llm", "gpt", "model", "claude", "gemini", "openai", "anthropic",
                    "mistral", "transformer", "diffusion", "agent", "inference"},
    "Chips & Hardware": {"chip", "gpu", "cpu", "nvidia", "amd", "intel", "hardware",
                         "semiconductor", "tpu", "wafer"},
    "Dev Tools": {"developer", "sdk", "github", "open source", "framework", "library",
                  "vscode", "cursor", "copilot", "ide", "cli"},
    "Web & Infrastructure": {"cloud", "kubernetes", "docker", "aws", "azure", "gcp",
                              "serverless", "database", "postgres", "redis"},
    "Tech Business": {"funding", "startup", "acquisition", "ipo", "valuation",
                      "revenue", "ceo", "layoff", "hire", "billion"},
    "Security & Privacy": {"security", "privacy", "breach", "vulnerability", "hack",
                            "encryption", "regulation", "gdpr", "ransomware"},
    "Consumer Tech": {"apple", "iphone", "android", "app", "wearable", "consumer",
                      "smartphone", "vision pro", "pixel"},
}


def _keyword_category(text: str) -> str:
    text = text.lower()
    scores = {cat: sum(1 for kw in kws if kw in text) for cat, kws in _KEYWORD_SETS.items()}
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "Tech Business"


def _keyword_fingerprint(text: str) -> set[str]:
    text = text.lower()
    all_kws: set[str] = set()
    for kws in _KEYWORD_SETS.values():
        all_kws |= kws
    return {kw for kw in all_kws if kw in text}


def _fallback_cluster(articles: list[Article]) -> list[dict]:
    fingerprints = {
        a.id: _keyword_fingerprint((a.title or "") + " " + (a.raw_content or "")[:500])
        for a in articles
    }
    clustered: set[int] = set()
    clusters: list[dict] = []
    for a in articles:
        if a.id in clustered:
            continue
        group = [a.id]
        clustered.add(a.id)
        for b in articles:
            if b.id in clustered:
                continue
            if len(fingerprints[a.id] & fingerprints[b.id]) >= 2:
                group.append(b.id)
                clustered.add(b.id)
        rep_title = next((x.title or "" for x in articles if x.id == a.id), "")
        clusters.append({
            "article_ids": group,
            "category": _keyword_category(rep_title),
            "headline": rep_title,
        })
    return clusters


# ---------------------------------------------------------------------------
# Batch helper (Claude has context limits)
# ---------------------------------------------------------------------------

BATCH_SIZE = 40


def _batch_cluster(articles: list[Article]) -> list[dict]:
    """Run Claude clustering in batches; merge results."""
    all_clusters: list[dict] = []
    for i in range(0, len(articles), BATCH_SIZE):
        batch = articles[i: i + BATCH_SIZE]
        result = _cluster_with_claude(batch)
        if result is None:
            logger.warning("Falling back to keyword clustering for batch %d", i // BATCH_SIZE)
            result = _fallback_cluster(batch)
        all_clusters.extend(result)
    return all_clusters


# ---------------------------------------------------------------------------
# Trend detection
# ---------------------------------------------------------------------------

def _update_trends(category_counts: dict[str, int], db) -> None:
    today = datetime.utcnow().date()
    for category, count in category_counts.items():
        trend = db.query(Trend).filter(Trend.topic == category).first()
        if trend:
            # Count as a new active day if we haven't updated today yet
            last_date = trend.last_seen.date() if trend.last_seen else None
            if last_date != today:
                trend.days_active += 1
            trend.mention_count += count
            trend.last_seen = datetime.utcnow()
            # Momentum: mentions × sqrt(days) so long-running trends don't dominate forever
            import math
            trend.momentum_score = round(trend.mention_count * math.sqrt(trend.days_active), 2)
        else:
            db.add(Trend(
                topic=category,
                mention_count=count,
                days_active=1,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                momentum_score=float(count),
            ))


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def run_cluster(article_ids: list[int], db) -> list[int]:
    """Cluster articles into stories; return list of new story IDs."""
    articles = db.query(Article).filter(Article.id.in_(article_ids)).all()
    if not articles:
        return []

    clusters = _batch_cluster(articles)

    # Build lookup: article_id → Article object
    article_map = {a.id: a for a in articles}

    story_ids: list[int] = []
    category_counts: dict[str, int] = defaultdict(int)

    for cluster_data in clusters:
        ids_in_cluster = [i for i in cluster_data["article_ids"] if i in article_map]
        if not ids_in_cluster:
            continue

        cluster_articles = [article_map[i] for i in ids_in_cluster]
        # Representative = lowest tier number (most authoritative source)
        rep = min(cluster_articles, key=lambda a: a.source_tier)

        category = cluster_data.get("category") or _keyword_category(rep.title or "")
        headline = cluster_data.get("headline") or rep.title or "Untitled"

        story = Story(
            headline=headline,
            summary="",
            category=category,
            importance_score=0.0,
            source_count=len(ids_in_cluster),
            published_at=rep.scraped_at,
            cluster_id=str(uuid.uuid4()),
        )
        db.add(story)
        db.flush()

        for aid in ids_in_cluster:
            db.add(StorySource(story_id=story.id, article_id=aid))

        story_ids.append(story.id)
        category_counts[category] += 1

    _update_trends(category_counts, db)
    db.commit()
    logger.info(
        "Cluster: %d articles → %d stories (Claude + fallback)",
        len(article_ids), len(story_ids),
    )
    return story_ids
