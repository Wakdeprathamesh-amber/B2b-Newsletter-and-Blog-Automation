"""Human Gate 2 — Content Review.

Pipeline pauses for human review of all 19 drafts.
Reviewer can: approve, request edits (with comments), or block individual drafts.
Max 2 revision rounds per draft.

Per spec:
- 48h deadline, 24h reminder, 48h escalation, 72h auto-pause
- [NEEDS EDIT] → AI revises with comment → reviewer re-checks
- [BLOCK] → draft cancelled, reason required
- Max 2 revision rounds per draft
"""

import structlog
from langgraph.types import interrupt

from src.graph.state import PipelineState
from src.models.enums import CycleStatus, DraftStatus
from src.models.schemas import ReviewSession

log = structlog.get_logger()


async def gate2_notify(state: PipelineState) -> dict:
    """Send Slack notification for content review."""

    cycle = state.cycle
    all_drafts = state.linkedin_drafts + state.blog_drafts
    if state.newsletter_draft:
        all_drafts.append(state.newsletter_draft)

    log.info("gate2_notify", cycle_id=cycle.cycle_id, draft_count=len(all_drafts))

    # TODO: Send Slack notification with review doc link
    # slack_message = f"Content review ready: {state.review_doc_url}"

    updated_cycle = cycle.model_copy(
        update={"status": CycleStatus.AWAITING_CONTENT_REVIEW}
    )
    return {"cycle": updated_cycle}


async def gate2_wait(state: PipelineState) -> dict:
    """Pause pipeline for content review. Resume with reviewer decisions."""

    cycle = state.cycle
    log.info("gate2_waiting", cycle_id=cycle.cycle_id, revision_round=state.revision_round)

    # Collect all draft IDs for the interrupt payload
    all_drafts = state.linkedin_drafts + state.blog_drafts
    if state.newsletter_draft:
        all_drafts.append(state.newsletter_draft)

    draft_summaries = [
        {
            "draft_id": d.draft_id,
            "channel": d.channel,
            "voice": d.voice,
            "topic_id": d.topic_id,
            "word_count": d.word_count,
            "flags": d.validation_flags,
            "status": d.status,
        }
        for d in all_drafts
    ]

    human_response = interrupt(
        {
            "gate": "content_review",
            "cycle_id": cycle.cycle_id,
            "review_doc_url": state.review_doc_url,
            "revision_round": state.revision_round,
            "message": f"Review round {state.revision_round + 1}. Approve, request edits, or block each draft.",
            "drafts": draft_summaries,
        }
    )

    # ── Process reviewer decisions ──
    reviewer = human_response.get("reviewer_name", "unknown")
    decisions = human_response.get("decisions", [])

    session = ReviewSession(
        cycle_id=cycle.cycle_id,
        gate="ContentReview",
        reviewer_name=reviewer,
        decisions=decisions,
    )

    drafts_to_revise = []

    # Build a lookup of all drafts
    all_draft_lookup = {}
    for d in state.linkedin_drafts:
        all_draft_lookup[d.draft_id] = d
    for d in state.blog_drafts:
        all_draft_lookup[d.draft_id] = d
    if state.newsletter_draft:
        all_draft_lookup[state.newsletter_draft.draft_id] = state.newsletter_draft

    for decision in decisions:
        draft_id = decision.get("item_id")
        action = decision.get("action")
        comment = decision.get("comment", "")

        draft = all_draft_lookup.get(draft_id)
        if not draft:
            continue

        if action == "Approved":
            draft.status = DraftStatus.APPROVED

        elif action == "NeedsEdit":
            draft.status = DraftStatus.REVISION_REQUESTED
            draft.review_comments = comment
            drafts_to_revise.append(draft_id)

        elif action == "Blocked":
            draft.status = DraftStatus.BLOCKED
            draft.review_comments = comment

    # Check if we need revision
    from datetime import datetime

    if drafts_to_revise:
        updated_cycle = cycle.model_copy(update={"status": CycleStatus.RUNNING, "stage": 5})
        return {
            "gate2_approved": False,
            "gate2_session": session,
            "drafts_needing_revision": drafts_to_revise,
            "revision_round": state.revision_round + 1,
            "cycle": updated_cycle,
        }
    else:
        updated_cycle = cycle.model_copy(
            update={
                "status": CycleStatus.PUBLISHING,
                "stage": 6,
                "content_approved_at": datetime.utcnow(),
            }
        )
        return {
            "gate2_approved": True,
            "gate2_session": session,
            "drafts_needing_revision": [],
            "cycle": updated_cycle,
        }
