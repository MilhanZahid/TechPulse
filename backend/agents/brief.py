"""Brief Agent — writes headline and 2-line summary for each story cluster using Groq."""
import logging
import os

from groq import Groq

from db.models import Story, Article, StorySource

logger = logging.getLogger(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

BRIEF_PROMPT = """\
You are a tech journalist writing a concise news brief. Given the following article(s) about the same tech story, produce:
1. A clean, clear headline (max 12 words)
2. A 2-sentence summary: first sentence = what happened, second = why it matters

Raw content:
{content}

Respond in this exact format:
HEADLINE: <headline here>
SUMMARY: <two-sentence summary here>
IMPORTANCE: <integer 1-10 reflecting how significant this is for the tech industry>
"""


def _build_content_snippet(story_id: int, db) -> str:
    sources = db.query(StorySource).filter(StorySource.story_id == story_id).all()
    snippets: list[str] = []
    for s in sources[:3]:
        article = db.query(Article).filter(Article.id == s.article_id).first()
        if article:
            text = (article.title or "") + "\n" + (article.raw_content or "")[:1000]
            snippets.append(f"[{article.source_name}]\n{text}")
    return "\n\n---\n\n".join(snippets)


def run_brief(story_ids: list[int], db) -> None:
    """Generate headline, summary, and importance score for each story."""
    for sid in story_ids:
        story = db.query(Story).filter(Story.id == sid).first()
        if not story or story.summary:
            continue

        content = _build_content_snippet(sid, db)
        if not content.strip():
            story.summary = "No content available."
            continue

        try:
            response = client.chat.completions.create(
                model=MODEL,
                max_tokens=400,
                messages=[{"role": "user", "content": BRIEF_PROMPT.format(content=content)}],
            )
            text = response.choices[0].message.content.strip()
            headline = _parse_field(text, "HEADLINE")
            summary = _parse_field(text, "SUMMARY")
            importance = _parse_field(text, "IMPORTANCE")

            if headline:
                story.headline = headline
            if summary:
                story.summary = summary
            if importance:
                try:
                    story.importance_score = float(importance)
                except ValueError:
                    pass

        except Exception as exc:
            logger.warning("Brief agent failed for story %d: %s", sid, exc)
            if not story.summary:
                story.summary = story.headline or "No summary available."

    db.commit()
    logger.info("Brief: wrote summaries for %d stories", len(story_ids))


def _parse_field(text: str, field: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"{field}:"):
            return line[len(field) + 1:].strip()
    return ""
