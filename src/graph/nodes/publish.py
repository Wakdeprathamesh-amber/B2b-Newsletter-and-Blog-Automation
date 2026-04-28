"""Stage 6 — Formatting and Publishing.

Three parallel publish nodes:
- 6A: LinkedIn → Buffer or native API, staggered schedule
- 6B: Blog → CMS (Notion or equivalent)
- 6C: Newsletter → HubSpot/Mailchimp

Per spec:
- LinkedIn: stagger by voice (Amber → +1 day → Madhur → +1 day → Jools)
- Blog: push to CMS as draft, human adds image + hits publish
- Newsletter: push to email tool as draft, human confirms send list + schedules
"""

from datetime import datetime, timedelta

import structlog

from src.graph.state import PipelineState
from src.models.enums import DraftStatus

log = structlog.get_logger()


async def publish_linkedin(state: PipelineState) -> dict:
    """Stage 6A: Format and queue LinkedIn posts for publishing."""

    approved = [d for d in state.linkedin_drafts if d.status == DraftStatus.APPROVED]
    published_ids: list[str] = []

    log.info("stage6a_start", approved_count=len(approved))

    # Build a staggered posting schedule
    # Topic 1 first (most urgent), within each topic: Amber → Madhur → Jools
    schedule_base = datetime.utcnow().replace(hour=9, minute=0, second=0)
    day_offset = 0

    # Group by topic, then voice order
    voice_order = {"AmberBrand": 0, "Madhur": 1, "Jools": 2}
    approved.sort(key=lambda d: (
        next((t.rank for t in state.shortlisted_topics if t.topic_id == d.topic_id), 99),
        voice_order.get(d.voice, 99),
    ))

    last_voice = None
    for draft in approved:
        # Stagger: new voice = next day
        if last_voice and draft.voice != last_voice:
            day_offset += 1

        scheduled_time = schedule_base + timedelta(days=day_offset)

        # TODO: Queue via Buffer API or LinkedIn Marketing API
        # buffer_client.create_update(
        #     profile_ids=[profile_id_for_voice(draft.voice)],
        #     text=draft.content_body,
        #     scheduled_at=scheduled_time.isoformat(),
        # )

        draft.status = DraftStatus.PUBLISHED
        draft.published_at = scheduled_time
        published_ids.append(draft.draft_id)
        last_voice = draft.voice

    log.info("stage6a_complete", scheduled_count=len(published_ids))

    # TODO: Send schedule preview to Slack for 2-hour cancellation window

    return {"published_draft_ids": published_ids}


async def publish_blogs(state: PipelineState) -> dict:
    """Stage 6B: Push blog drafts to CMS as drafts."""

    approved = [d for d in state.blog_drafts if d.status == DraftStatus.APPROVED]
    published_ids: list[str] = []

    log.info("stage6b_start", approved_count=len(approved))

    for draft in approved:
        # TODO: Push to Notion / CMS via API
        # - Convert markdown H1/H2 to CMS format
        # - Create [STAT] callout box
        # - Add author bio based on audience
        # - Generate meta description from first paragraph
        # notion_client.pages.create(
        #     parent={"database_id": BLOG_DB_ID},
        #     properties={...},
        #     children=[...blocks...],
        # )

        draft.status = DraftStatus.PUBLISHED
        published_ids.append(draft.draft_id)

    log.info("stage6b_complete", pushed_count=len(published_ids))

    # TODO: Notify blog publisher via Slack
    # "3 blog drafts ready in CMS. Please add images and schedule."

    return {"published_draft_ids": published_ids}


async def publish_newsletter(state: PipelineState) -> dict:
    """Stage 6C: Push newsletter to email tool as draft."""

    newsletter = state.newsletter_draft
    published_ids: list[str] = []

    if not newsletter or newsletter.status != DraftStatus.APPROVED:
        log.info("stage6c_no_newsletter")
        return {"published_draft_ids": []}

    log.info("stage6c_start")

    # TODO: Push to HubSpot/Mailchimp
    # - Map sections into email template
    # - Set subject line: "[Amber Beat] {month} {year} — {theme}"
    # - Set preview text: first sentence of UK section
    # hubspot_client.marketing.transactional.single_send_api.send_email(...)

    newsletter.status = DraftStatus.PUBLISHED
    published_ids.append(newsletter.draft_id)

    log.info("stage6c_complete")

    # TODO: Notify newsletter sender via Slack
    # "Newsletter draft ready in HubSpot. Please review render and schedule send."

    return {"published_draft_ids": published_ids}
