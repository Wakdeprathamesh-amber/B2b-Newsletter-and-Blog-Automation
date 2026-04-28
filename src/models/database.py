"""SQLAlchemy ORM models and database setup."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from src.settings import settings


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())[:12]


# -- Signal --

class SignalRow(Base):
    __tablename__ = "signals"

    signal_id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_new_id)
    cycle_id: Mapped[str] = mapped_column(String(32), index=True)
    source_name: Mapped[str] = mapped_column(String(128))
    source_url: Mapped[str] = mapped_column(Text)
    headline: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    published_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    region: Mapped[str] = mapped_column(String(32))
    topic_category: Mapped[str] = mapped_column(String(64))
    raw_content: Mapped[str] = mapped_column(Text, default="")
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    is_negative_news: Mapped[bool] = mapped_column(Boolean, default=False)
    mentions_competitor: Mapped[bool] = mapped_column(Boolean, default=False)
    is_politically_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    is_opinion: Mapped[bool] = mapped_column(Boolean, default=False)
    tagging_failed: Mapped[bool] = mapped_column(Boolean, default=False)


# -- Topic --

class TopicRow(Base):
    __tablename__ = "topics"

    topic_id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_new_id)
    cycle_id: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(256))
    summary: Mapped[str] = mapped_column(Text)
    rank: Mapped[int] = mapped_column(Integer)
    urgency: Mapped[str] = mapped_column(String(32))
    primary_region: Mapped[str] = mapped_column(String(32))
    secondary_regions: Mapped[list] = mapped_column(JSON, default=list)
    stakeholder_tags: Mapped[list] = mapped_column(JSON, default=list)
    source_signal_ids: Mapped[list] = mapped_column(JSON, default=list)
    rationale: Mapped[str] = mapped_column(Text, default="")
    content_guidance: Mapped[str] = mapped_column(Text, default="")

    urgency_score: Mapped[float] = mapped_column(Float, default=0.0)
    regional_relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    stakeholder_fit_score: Mapped[float] = mapped_column(Float, default=0.0)
    total_score: Mapped[float] = mapped_column(Float, default=0.0)

    status: Mapped[str] = mapped_column(String(32), default="Pending")
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    edited_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    edited_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    performance_score: Mapped[float | None] = mapped_column(Float, nullable=True)


# -- ContentDraft --

class ContentDraftRow(Base):
    __tablename__ = "content_drafts"

    draft_id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_new_id)
    cycle_id: Mapped[str] = mapped_column(String(32), index=True)
    topic_id: Mapped[str] = mapped_column(String(16))
    channel: Mapped[str] = mapped_column(String(32))
    audience: Mapped[str | None] = mapped_column(String(32), nullable=True)
    voice: Mapped[str] = mapped_column(String(32))
    content_body: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    generation_prompt: Mapped[str] = mapped_column(Text, default="")
    generation_model: Mapped[str] = mapped_column(String(64), default="")
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    status: Mapped[str] = mapped_column(String(32), default="Draft")
    review_comments: Mapped[str] = mapped_column(Text, default="")
    revised_body: Mapped[str] = mapped_column(Text, default="")
    revised_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revision_count: Mapped[int] = mapped_column(Integer, default=0)
    validation_flags: Mapped[list] = mapped_column(JSON, default=list)

    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_url: Mapped[str] = mapped_column(Text, default="")


# -- Cycle --

class CycleRow(Base):
    __tablename__ = "cycles"

    cycle_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    stage: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="Running")

    topics_approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    content_approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    error_log: Mapped[list] = mapped_column(JSON, default=list)
    signal_count: Mapped[int] = mapped_column(Integer, default=0)
    topic_count: Mapped[int] = mapped_column(Integer, default=0)
    draft_count: Mapped[int] = mapped_column(Integer, default=0)


# -- ReviewSession --

class ReviewSessionRow(Base):
    __tablename__ = "review_sessions"

    session_id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_new_id)
    cycle_id: Mapped[str] = mapped_column(String(32), index=True)
    gate: Mapped[str] = mapped_column(String(32))
    reviewer_name: Mapped[str] = mapped_column(String(128))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decisions: Mapped[list] = mapped_column(JSON, default=list)


# -- LogEntry --

class LogEntryRow(Base):
    __tablename__ = "log_entries"

    log_id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_new_id)
    cycle_id: Mapped[str] = mapped_column(String(32), index=True)
    stage: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str] = mapped_column(String(16))
    actor: Mapped[str] = mapped_column(String(128))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)


# -- Engine + Session --

engine = create_engine(
    settings.database_url,
    echo=False,
    # SQLite needs this for JSON column support
    **({"connect_args": {"check_same_thread": False}} if "sqlite" in settings.database_url else {}),
)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(engine)


def get_db() -> Session:
    """Get a database session (for FastAPI dependency injection)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
