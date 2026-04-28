"""Revision Node — Revises flagged drafts based on reviewer comments.

Called when Gate 2 returns drafts with [NEEDS EDIT].
Max 2 revision rounds per the spec.
Only revises the flagged drafts — approved drafts are untouched.
"""

import structlog

from src.graph.state import PipelineState
from src.llm import complete
from src.models.enums import DraftStatus
from src.models.schemas import ContentDraft
from src.settings import settings

log = structlog.get_logger()


async def revise_drafts(state: PipelineState) -> dict:
    """Revise only the drafts that were flagged for revision."""

    draft_ids = state.drafts_needing_revision
    revision_round = state.revision_round

    log.info(
        "revision_start",
        cycle_id=state.cycle.cycle_id,
        round=revision_round,
        draft_count=len(draft_ids),
    )

    # Collect all drafts into a mutable list
    all_linkedin = list(state.linkedin_drafts)
    all_blogs = list(state.blog_drafts)
    newsletter = state.newsletter_draft

    async def _revise_single(draft: ContentDraft) -> ContentDraft:
        """Revise a single draft using the reviewer's comments."""
        revision_prompt = f"""You are revising a content draft based on reviewer feedback.

ORIGINAL DRAFT:
{draft.content_body}

REVIEWER COMMENTS:
{draft.review_comments}

CHANNEL: {draft.channel}
VOICE: {draft.voice}

Rewrite the draft incorporating the reviewer's feedback.
Maintain the same topic, voice, and format.
Return ONLY the revised content."""

        try:
            revised_body = await complete(
                role="generation",
                messages=[{"role": "user", "content": revision_prompt}],
                max_tokens=4000,
            )

            from datetime import datetime

            draft.revised_body = revised_body
            draft.content_body = revised_body
            draft.word_count = len(draft.content_body.split())
            draft.revised_at = datetime.utcnow()
            draft.revision_count += 1
            draft.status = DraftStatus.UNDER_REVIEW

        except Exception as e:
            log.error("revision_failed", draft_id=draft.draft_id, error=str(e))

        return draft

    # Revise LinkedIn drafts
    for i, draft in enumerate(all_linkedin):
        if draft.draft_id in draft_ids:
            all_linkedin[i] = await _revise_single(draft)

    # Revise blog drafts
    for i, draft in enumerate(all_blogs):
        if draft.draft_id in draft_ids:
            all_blogs[i] = await _revise_single(draft)

    # Revise newsletter
    if newsletter and newsletter.draft_id in draft_ids:
        newsletter = await _revise_single(newsletter)

    log.info("revision_complete", round=revision_round)

    return {
        "linkedin_drafts": all_linkedin,
        "blog_drafts": all_blogs,
        "newsletter_draft": newsletter,
    }
