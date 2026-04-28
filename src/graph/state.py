"""Pipeline state that flows through the LangGraph graph.

This is the single state object that every node reads from and writes to.
LangGraph checkpoints this automatically -- so if the pipeline pauses at a
human gate for 48 hours, or crashes mid-stage, the full state is preserved.
"""

from typing import Annotated

from pydantic import BaseModel, Field

from src.models.schemas import ContentDraft, Cycle, ReviewSession, Signal, Topic


def _merge_lists(left: list, right: list) -> list:
    """Reducer: append new items to existing list (used for signals, errors)."""
    return left + right


def _replace(left, right):
    """Reducer: always take the newer value."""
    return right


class PipelineState(BaseModel):
    """The complete state of a single content cycle.

    LangGraph persists this between nodes. Each node receives the full state
    and returns a partial update (only the fields it changed).

    Reducers control how partial updates merge:
    - Signals and errors: new items are appended (_merge_lists)
    - Drafts, topics, scalars: new value replaces old (_replace)
      This is critical for the revision loop -- revise_drafts returns
      the full updated draft lists, not just new items.
    """

    # -- Cycle metadata --
    cycle: Annotated[Cycle | None, _replace] = None

    # -- Stage 1 output --
    signals: Annotated[list[Signal], _merge_lists] = Field(default_factory=list)

    # -- Stage 2 output --
    ranked_topics: Annotated[list[Topic], _replace] = Field(default_factory=list)

    # -- Stage 3 output --
    shortlisted_topics: Annotated[list[Topic], _replace] = Field(default_factory=list)

    # -- Human Gate 1 --
    gate1_approved: Annotated[bool, _replace] = False
    gate1_session: Annotated[ReviewSession | None, _replace] = None

    # -- Stage 4 outputs --
    # Using _replace so revision node can return the full updated list
    # without duplicating entries
    linkedin_drafts: Annotated[list[ContentDraft], _replace] = Field(default_factory=list)
    blog_drafts: Annotated[list[ContentDraft], _replace] = Field(default_factory=list)
    newsletter_draft: Annotated[ContentDraft | None, _replace] = None

    # -- Newsroom blog (weekly): 7-12 items per region, 21-25 words each --
    # Dict keyed by region: {"UK": [{item_text, topic_id, source_url, ...}], ...}
    newsroom_items: Annotated[dict, _replace] = Field(default_factory=dict)

    # -- Stage 5 --
    review_doc_url: Annotated[str, _replace] = ""

    # -- Human Gate 2 --
    gate2_approved: Annotated[bool, _replace] = False
    gate2_session: Annotated[ReviewSession | None, _replace] = None
    drafts_needing_revision: Annotated[list[str], _replace] = Field(
        default_factory=list, description="draft_ids that need revision"
    )
    revision_round: Annotated[int, _replace] = 0

    # -- Stage 6 --
    published_draft_ids: Annotated[list[str], _merge_lists] = Field(default_factory=list)

    # -- Stage 7 --
    performance_report: Annotated[dict, _replace] = Field(default_factory=dict)

    # -- Error tracking --
    errors: Annotated[list[str], _merge_lists] = Field(default_factory=list)
