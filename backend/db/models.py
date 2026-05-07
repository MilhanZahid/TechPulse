from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime,
    Boolean, ForeignKey, ARRAY
)
from sqlalchemy.orm import relationship
from db.connection import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    url = Column(Text, unique=True, nullable=False)
    source_name = Column(String(255), nullable=False)
    source_tier = Column(Integer, nullable=False)
    raw_content = Column(Text)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    relevance_score = Column(Float, default=0.0)

    story_sources = relationship("StorySource", back_populates="article")


class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    headline = Column(Text, nullable=False)
    summary = Column(Text)
    category = Column(String(100))
    importance_score = Column(Float, default=0.0)
    source_count = Column(Integer, default=1)
    image_url = Column(Text)
    published_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    cluster_id = Column(String(255))

    story_sources = relationship("StorySource", back_populates="story")
    chats = relationship("StoryChat", back_populates="story")


class StorySource(Base):
    __tablename__ = "story_sources"

    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)

    story = relationship("Story", back_populates="story_sources")
    article = relationship("Article", back_populates="story_sources")


class Trend(Base):
    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(255), nullable=False)
    mention_count = Column(Integer, default=1)
    days_active = Column(Integer, default=1)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    momentum_score = Column(Float, default=0.0)


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    tier = Column(Integer, nullable=False)
    scrape_type = Column(String(50), nullable=False)  # web, rss, api
    last_scraped = Column(DateTime)
    is_active = Column(Boolean, default=True)


class ScheduleConfig(Base):
    __tablename__ = "schedule_config"

    id = Column(Integer, primary_key=True, index=True)
    refresh_times = Column(ARRAY(String), default=list)
    timezone = Column(String(100), default="UTC")
    is_active = Column(Boolean, default=True)


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    interested_categories = Column(ARRAY(String), default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    articles_scraped = Column(Integer, default=0)
    stories_processed = Column(Integer, default=0)
    status = Column(String(50), default="running")  # running, completed, failed
    error_log = Column(Text)


class StoryChat(Base):
    __tablename__ = "story_chats"

    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    story = relationship("Story", back_populates="chats")
