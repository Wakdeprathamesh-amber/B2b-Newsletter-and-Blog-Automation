"""Persistence helpers -- write pipeline state to the SQL database.

Each function takes Pydantic models from the pipeline state and persists
them to the corresponding SQLAlchemy ORM rows. Also handles audit logging.
"""

from datetime import datetime, timezone

from src.models.database import (
    ContentDraftRow,
    CycleRow,
    LogEntryRow,
    ReviewSessionRow,
    SessionLocal,
    SignalRow,
    TopicRow,
)
from src.models.schemas import ContentDraft, Cycle, LogEntry, ReviewSession, Signal, Topic


def _now() -> datetime:
    return datetime.now(timezone.utc)


def persist_cycle(cycle: Cycle) -> None:
    """Upsert a Cycle record."""
    with SessionLocal() as db:
        existing = db.get(CycleRow, cycle.cycle_id)
        if existing:
            existing.stage = cycle.stage
            existing.status = cycle.status
            existing.signal_count = cycle.signal_count
            existing.topic_count = cycle.topic_count
            existing.draft_count = cycle.draft_count
            existing.topics_approved_at = cycle.topics_approved_at
            existing.content_approved_at = cycle.content_approved_at
            existing.completed_at = cycle.completed_at
            existing.error_log = cycle.error_log
        else:
            db.add(CycleRow(
                cycle_id=cycle.cycle_id,
                started_at=cycle.started_at,
                stage=cycle.stage,
                status=cycle.status,
                signal_count=cycle.signal_count,
                topic_count=cycle.topic_count,
                draft_count=cycle.draft_count,
            ))
        db.commit()


def persist_signals(signals: list[Signal]) -> None:
    """Insert Signal records (skip duplicates by signal_id)."""
    with SessionLocal() as db:
        for sig in signals:
            if sig.signal_id and db.get(SignalRow, sig.signal_id):
                continue
            row = SignalRow(
                signal_id=sig.signal_id or None,
                cycle_id=sig.cycle_id,
                source_name=sig.source_name,
                source_url=sig.source_url,
                headline=sig.headline,
                summary=sig.summary,
                published_date=sig.published_date,
                region=sig.region,
                topic_category=sig.topic_category,
                raw_content=sig.raw_content[:5000] if sig.raw_content else "",
                is_negative_news=sig.is_negative_news,
                mentions_competitor=sig.mentions_competitor,
                is_politically_sensitive=sig.is_politically_sensitive,
                tagging_failed=sig.tagging_failed,
            )
            db.add(row)
        db.commit()


def persist_topics(topics: list[Topic]) -> None:
    """Upsert Topic records."""
    with SessionLocal() as db:
        for topic in topics:
            existing = db.get(TopicRow, topic.topic_id) if topic.topic_id else None
            if existing:
                existing.title = topic.title
                existing.summary = topic.summary
                existing.rank = topic.rank
                existing.status = topic.status
                existing.approved_by = topic.approved_by
                existing.approved_at = topic.approved_at
                existing.edited_title = topic.edited_title
                existing.edited_summary = topic.edited_summary
                existing.content_guidance = topic.content_guidance
            else:
                db.add(TopicRow(
                    topic_id=topic.topic_id or None,
                    cycle_id=topic.cycle_id,
                    title=topic.title,
                    summary=topic.summary,
                    rank=topic.rank,
                    urgency=topic.urgency,
                    primary_region=topic.primary_region,
                    secondary_regions=topic.secondary_regions,
                    stakeholder_tags=topic.stakeholder_tags,
                    source_signal_ids=topic.source_signal_ids,
                    rationale=topic.rationale,
                    content_guidance=topic.content_guidance,
                    urgency_score=topic.urgency_score,
                    regional_relevance_score=topic.regional_relevance_score,
                    stakeholder_fit_score=topic.stakeholder_fit_score,
                    total_score=topic.total_score,
                    status=topic.status,
                ))
        db.commit()


def persist_drafts(drafts: list[ContentDraft]) -> None:
    """Upsert ContentDraft records."""
    with SessionLocal() as db:
        for draft in drafts:
            existing = db.get(ContentDraftRow, draft.draft_id) if draft.draft_id else None
            if existing:
                existing.content_body = draft.content_body
                existing.word_count = draft.word_count
                existing.status = draft.status
                existing.review_comments = draft.review_comments
                existing.revised_body = draft.revised_body
                existing.revised_at = draft.revised_at
                existing.revision_count = draft.revision_count
                existing.published_at = draft.published_at
                existing.published_url = draft.published_url
                existing.validation_flags = draft.validation_flags
            else:
                db.add(ContentDraftRow(
                    draft_id=draft.draft_id or None,
                    cycle_id=draft.cycle_id,
                    topic_id=draft.topic_id,
                    channel=draft.channel,
                    audience=draft.audience,
                    voice=draft.voice,
                    content_body=draft.content_body,
                    word_count=draft.word_count,
                    generation_prompt=draft.generation_prompt,
                    generation_model=draft.generation_model,
                    status=draft.status,
                    validation_flags=draft.validation_flags,
                ))
        db.commit()


def persist_review_session(session: ReviewSession) -> None:
    """Insert a ReviewSession record."""
    with SessionLocal() as db:
        db.add(ReviewSessionRow(
            session_id=session.session_id or None,
            cycle_id=session.cycle_id,
            gate=session.gate,
            reviewer_name=session.reviewer_name,
            started_at=session.started_at,
            completed_at=session.completed_at,
            decisions=[d.model_dump() for d in session.decisions],
        ))
        db.commit()


def write_log(
    cycle_id: str,
    stage: int,
    event_type: str,
    entity_type: str,
    entity_id: str,
    actor: str = "system",
    details: dict | None = None,
) -> None:
    """Write a single audit log entry."""
    with SessionLocal() as db:
        db.add(LogEntryRow(
            cycle_id=cycle_id,
            stage=stage,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            details=details or {},
        ))
        db.commit()
