"""Insight Agent — generates project ideas from current trends. /lab only."""
import logging
import os

from groq import Groq

from db.models import Story, Trend

logger = logging.getLogger(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

IDEAS_PROMPT = """\
You are a product strategist. Based on today's top tech stories and rising trends, generate 3-5 actionable project ideas for a developer to build.

Today's top stories:
{stories}

Rising trends:
{trends}

For each idea, respond in this EXACT format (repeat the block for each idea):

---
PROJECT: <project name>
PITCH: <one-line pitch>
WHY NOW: <why current trends make this relevant>
STACK: <suggested tech stack>
DIFFICULTY: <Easy | Medium | Hard>
BUILD TIME: <estimated build time>
---
"""


def generate_ideas(db) -> str:
    """Generate project ideas based on today's stories and trends."""
    from datetime import datetime, timedelta
    from sqlalchemy import desc

    cutoff = datetime.utcnow() - timedelta(hours=24)
    stories = (
        db.query(Story)
        .filter(Story.created_at >= cutoff)
        .order_by(desc(Story.importance_score))
        .limit(10)
        .all()
    )
    trends = db.query(Trend).order_by(desc(Trend.momentum_score)).limit(5).all()

    stories_text = "\n".join(
        f"- [{s.category}] {s.headline}: {s.summary}" for s in stories
    )
    trends_text = "\n".join(
        f"- {t.topic} (momentum: {t.momentum_score:.0f}, active {t.days_active} days)"
        for t in trends
    )

    if not stories_text:
        return "No stories available yet. Run a scrape first."

    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": IDEAS_PROMPT.format(stories=stories_text, trends=trends_text),
            }],
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("Insight agent failed: %s", exc)
        return "Could not generate ideas at this time."
