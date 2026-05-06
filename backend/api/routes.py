from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.connection import get_db
from db.models import Story, Trend, Article, StorySource, ScheduleConfig, UserPreferences, PipelineRun, StoryChat
from api.middleware import require_admin

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class StoryOut(BaseModel):
    id: int
    headline: str
    summary: str | None
    category: str | None
    importance_score: float
    source_count: int
    image_url: str | None
    published_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class TrendOut(BaseModel):
    id: int
    topic: str
    mention_count: int
    days_active: int
    momentum_score: float
    last_seen: datetime

    class Config:
        from_attributes = True


class ScheduleIn(BaseModel):
    refresh_times: list[str]
    timezone: str = "UTC"
    is_active: bool = True


class PreferencesIn(BaseModel):
    interested_categories: list[str]


class ChatIn(BaseModel):
    message: str


class RefreshOut(BaseModel):
    run_id: int
    articles_scraped: int
    stories_processed: int
    status: str
    error: str | None


# ---------------------------------------------------------------------------
# Brief / stories
# ---------------------------------------------------------------------------

@router.get("/brief", response_model=dict[str, list[StoryOut]])
def get_brief(db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(hours=24)
    stories = (
        db.query(Story)
        .filter(Story.created_at >= cutoff)
        .order_by(desc(Story.importance_score))
        .all()
    )
    grouped: dict[str, list[StoryOut]] = {}
    for s in stories:
        cat = s.category or "Uncategorized"
        grouped.setdefault(cat, []).append(StoryOut.model_validate(s))
    return grouped


@router.get("/trends", response_model=list[TrendOut])
def get_trends(db: Session = Depends(get_db)):
    return db.query(Trend).order_by(desc(Trend.momentum_score)).limit(20).all()


@router.get("/interests", response_model=list[StoryOut])
def get_interests(db: Session = Depends(get_db)):
    prefs = db.query(UserPreferences).first()
    if not prefs or not prefs.interested_categories:
        return []
    cutoff = datetime.utcnow() - timedelta(hours=24)
    return (
        db.query(Story)
        .filter(
            Story.created_at >= cutoff,
            Story.category.in_(prefs.interested_categories),
        )
        .order_by(desc(Story.importance_score))
        .all()
    )


@router.get("/story/{story_id}", response_model=StoryOut)
def get_story(story_id: int, db: Session = Depends(get_db)):
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.post("/story/{story_id}/context")
async def get_story_context(story_id: int, db: Session = Depends(get_db)):
    from agents.context import generate_context
    explanation = generate_context(story_id, db)
    return {"explanation": explanation}


@router.post("/story/{story_id}/chat")
async def story_chat(story_id: int, body: ChatIn, db: Session = Depends(get_db)):
    from agents.context import chat
    reply = chat(story_id, body.message, db)
    return {"reply": reply}


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

@router.get("/schedule")
def get_schedule(db: Session = Depends(get_db)):
    config = db.query(ScheduleConfig).first()
    if not config:
        return {"refresh_times": [], "timezone": "UTC", "is_active": False}
    return config


@router.post("/schedule")
def update_schedule(body: ScheduleIn, db: Session = Depends(get_db)):
    config = db.query(ScheduleConfig).first()
    if not config:
        config = ScheduleConfig()
        db.add(config)
    config.refresh_times = body.refresh_times
    config.timezone = body.timezone
    config.is_active = body.is_active
    db.commit()
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------

@router.get("/preferences")
def get_preferences(db: Session = Depends(get_db)):
    prefs = db.query(UserPreferences).first()
    return {"interested_categories": prefs.interested_categories if prefs else []}


@router.post("/preferences")
def update_preferences(body: PreferencesIn, db: Session = Depends(get_db)):
    prefs = db.query(UserPreferences).first()
    if not prefs:
        prefs = UserPreferences()
        db.add(prefs)
    prefs.interested_categories = body.interested_categories
    db.commit()
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Manual refresh
# ---------------------------------------------------------------------------

@router.post("/refresh", response_model=RefreshOut)
async def manual_refresh(db: Session = Depends(get_db)):
    from agents.orchestrator import run_pipeline
    result = await run_pipeline()
    return RefreshOut(**result)


# ---------------------------------------------------------------------------
# Admin / Lab
# ---------------------------------------------------------------------------

@router.post("/lab/ideas", dependencies=[Depends(require_admin)])
async def lab_ideas(db: Session = Depends(get_db)):
    from agents.insight import generate_ideas
    ideas = generate_ideas(db)
    return {"ideas": ideas}


@router.get("/lab/status", dependencies=[Depends(require_admin)])
def lab_status(db: Session = Depends(get_db)):
    runs = (
        db.query(PipelineRun)
        .order_by(desc(PipelineRun.started_at))
        .limit(10)
        .all()
    )
    source_count = db.query(Article).count()
    story_count = db.query(Story).count()
    return {
        "recent_runs": [
            {
                "id": r.id,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
                "articles_scraped": r.articles_scraped,
                "stories_processed": r.stories_processed,
                "status": r.status,
                "error_log": r.error_log,
            }
            for r in runs
        ],
        "total_articles": source_count,
        "total_stories": story_count,
    }
