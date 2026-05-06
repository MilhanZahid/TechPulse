"""Context Agent — on-demand story explanation and follow-up chat using Groq."""
import logging
import os

from groq import Groq

from db.models import Story, Article, StorySource, StoryChat

logger = logging.getLogger(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

CONTEXT_PROMPT = """\
You are TechPulse, an intelligent tech analyst. A user just opened a news story. Generate a structured explanation.

Story headline: {headline}
Category: {category}

Source articles:
{articles}

Respond in this EXACT format (use these exact section headers):

## What happened
<Clear 2-3 sentence explanation of the specific event or announcement>

## Background context
<3-5 sentences explaining what the reader needs to know to understand this — assume they're smart but may not follow tech closely. Explain relevant companies, technologies, or history from scratch.>

## What to think about it
<3-4 sentences on implications: who is affected, what it signals for the industry, what to watch next>
"""


def _get_story_content(story_id: int, db) -> tuple[str, str, str]:
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        return "", "", ""

    sources = db.query(StorySource).filter(StorySource.story_id == story_id).all()
    snippets: list[str] = []
    for s in sources[:5]:
        article = db.query(Article).filter(Article.id == s.article_id).first()
        if article:
            snippets.append(
                f"[{article.source_name} — Tier {article.source_tier}]\n"
                f"{article.title}\n{(article.raw_content or '')[:1500]}"
            )

    return story.headline or "", story.category or "", "\n\n---\n\n".join(snippets)


def generate_context(story_id: int, db) -> str:
    """Generate the initial 3-section explanation for a story. Stores as first assistant message."""
    headline, category, articles_text = _get_story_content(story_id, db)
    if not headline:
        return "Story not found."

    # Check if already generated
    existing = (
        db.query(StoryChat)
        .filter(StoryChat.story_id == story_id, StoryChat.role == "assistant")
        .first()
    )
    if existing:
        return existing.content

    prompt = CONTEXT_PROMPT.format(
        headline=headline,
        category=category,
        articles=articles_text or "No full article content available.",
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        explanation = response.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("Context agent failed for story %d: %s", story_id, exc)
        explanation = "Could not generate explanation at this time."

    db.add(StoryChat(story_id=story_id, role="assistant", content=explanation))
    db.commit()
    return explanation


CHAT_SYSTEM = """\
You are TechPulse, an intelligent tech analyst. You already explained this story to the user.
Answer their follow-up questions clearly and concisely. Stay focused on the story and its implications.
If you don't know something, say so rather than speculating.
"""


def chat(story_id: int, user_message: str, db) -> str:
    """Handle a follow-up chat message about a story."""
    # Load conversation history
    history = (
        db.query(StoryChat)
        .filter(StoryChat.story_id == story_id)
        .order_by(StoryChat.created_at)
        .all()
    )

    messages = [{"role": msg.role, "content": msg.content} for msg in history]
    messages.append({"role": "user", "content": user_message})

    db.add(StoryChat(story_id=story_id, role="user", content=user_message))

    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=800,
            messages=[{"role": "system", "content": CHAT_SYSTEM}] + messages,
        )
        reply = response.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("Chat agent failed for story %d: %s", story_id, exc)
        reply = "Sorry, I couldn't process that question right now."

    db.add(StoryChat(story_id=story_id, role="assistant", content=reply))
    db.commit()
    return reply
