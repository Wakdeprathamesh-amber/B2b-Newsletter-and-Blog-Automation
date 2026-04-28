"""Pydantic models for the 6 core data entities defined in the product spec."""

from datetime import datetime

from pydantic import BaseModel, Field

from src.models.enums import (
    CycleStatus,
    DraftChannel,
    DraftStatus,
    DraftVoice,
    GateType,
    Region,
    StakeholderAudience,
    TopicCategory,
    TopicStatus,
    UrgencyLevel,
)


# ── 3.1 Signal ──────────────────────────────────────────────────────────────


class Signal(BaseModel):
    """A raw piece of information captured from a source."""

    signal_id: str = Field(default="", description="Unique identifier, set by DB")
    source_name: str
    source_url: str
    headline: str
    summary: str = Field(description="1-3 sentence summary")
    published_date: datetime | None = None
    region: Region
    topic_category: TopicCategory
    raw_content: str = ""
    captured_at: datetime = Field(default_factory=datetime.utcnow)
    cycle_id: str = ""

    # AI-assigned flags
    is_negative_news: bool = False
    mentions_competitor: bool = False
    is_politically_sensitive: bool = False
    is_opinion: bool = False
    is_pr_article: bool = False
    tagging_failed: bool = False

    # Filtering status — set during ingestion
    status: str = "Kept"  # Kept | Dropped (PR) | Dropped (Opinion) | Dropped (Irrelevant) | Dropped (Duplicate)


# ── 3.2 Topic ───────────────────────────────────────────────────────────────


class Topic(BaseModel):
    """A ranked editorial topic derived from one or more signals."""

    topic_id: str = Field(default="", description="Unique identifier, set by DB")
    cycle_id: str = ""
    title: str = Field(max_length=80, description="Short topic title, max ~10 words")
    summary: str = Field(description="What this topic is about and why it matters, 2-3 sentences")
    rank: int = Field(ge=1, le=60, description="1 = highest priority")
    urgency: UrgencyLevel
    primary_region: Region
    secondary_regions: list[Region] = []
    stakeholder_tags: list[StakeholderAudience] = []
    source_signal_ids: list[str] = Field(
        default=[], description="Signal IDs that support this topic"
    )
    source_urls: list[str] = Field(
        default=[], description="URLs of the source articles (for human reference)"
    )
    rationale: str = Field(default="", description="Why the AI ranked this topic here")
    content_guidance: str = Field(
        default="", description="1-2 sentences of editorial direction for content agents"
    )

    # Scoring (from Stage 2)
    urgency_score: float = 0.0
    regional_relevance_score: float = 0.0
    stakeholder_fit_score: float = 0.0
    total_score: float = 0.0

    # Human review state
    status: TopicStatus = TopicStatus.PENDING
    approved_by: str | None = None
    approved_at: datetime | None = None
    edited_title: str | None = None
    edited_summary: str | None = None

    # Feedback loop (Stage 7)
    performance_score: float | None = None


# ── 3.3 ContentDraft ────────────────────────────────────────────────────────


class ContentDraft(BaseModel):
    """A single piece of generated content."""

    draft_id: str = Field(default="", description="Unique identifier, set by DB")
    cycle_id: str = ""
    topic_id: str = ""
    channel: DraftChannel
    audience: StakeholderAudience | None = None
    voice: DraftVoice
    content_body: str
    word_count: int = 0
    generation_prompt: str = Field(
        default="", description="Exact prompt sent to AI, stored for auditability"
    )
    generation_model: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # Review state
    status: DraftStatus = DraftStatus.DRAFT
    review_comments: str = ""
    revised_body: str = ""
    revised_at: datetime | None = None
    revision_count: int = 0

    # Validation flags
    validation_flags: list[str] = Field(
        default=[], description="e.g. 'word_count_exceeded', 'missing_data_point'"
    )

    # Publishing
    published_at: datetime | None = None
    published_url: str = ""


# ── 3.4 Cycle ───────────────────────────────────────────────────────────────


class Cycle(BaseModel):
    """A single run of the full pipeline."""

    cycle_id: str = Field(description="e.g. '2025-W15'")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    stage: int = Field(default=1, ge=1, le=7, description="Current stage (1-7)")
    status: CycleStatus = CycleStatus.RUNNING

    topics_approved_at: datetime | None = None
    content_approved_at: datetime | None = None
    completed_at: datetime | None = None

    error_log: list[str] = []
    signal_count: int = 0
    topic_count: int = 0
    draft_count: int = 0


# ── 3.5 ReviewSession ──────────────────────────────────────────────────────


class ReviewDecision(BaseModel):
    """A single decision within a review session."""

    item_id: str
    action: str = Field(description="Approved | NeedsEdit | Blocked | Swapped | Rejected")
    comment: str = ""
    edited_title: str | None = None
    edited_summary: str | None = None
    swapped_with: str | None = None


class ReviewSession(BaseModel):
    """A logged record of a human review event."""

    session_id: str = Field(default="", description="Unique identifier, set by DB")
    cycle_id: str
    gate: GateType
    reviewer_name: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    decisions: list[ReviewDecision] = []


# ── 3.6 LogEntry ────────────────────────────────────────────────────────────


class LogEntry(BaseModel):
    """Audit log entry — every action in the system produces one."""

    log_id: str = Field(default="", description="Unique identifier, set by DB")
    cycle_id: str
    stage: int
    event_type: str = Field(
        description="signal_captured | topic_ranked | draft_generated | "
        "human_approved | published | error | etc."
    )
    entity_type: str = Field(description="Signal | Topic | ContentDraft | Cycle | ReviewSession")
    entity_id: str
    actor: str = Field(description="'system' or human name")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: dict = Field(default_factory=dict, description="Event-specific context")
