"""Stage 7 — Performance Feedback Loop.

Collects engagement data 7 days after publishing and feeds scores
back into the topic store for future cycle scoring.

Per spec:
- LinkedIn: impressions, clicks, reactions, comments, shares
- Email: open rate, CTR, unsubscribe count
- Calculate performance score per topic
- High-performing topics → boost in next cycle
- Low-performing / blocked topics → slight penalty
- Generate Cycle Performance Report → Slack
"""

import structlog

from src.graph.state import PipelineState
from src.models.enums import CycleStatus

log = structlog.get_logger()


async def collect_feedback(state: PipelineState) -> dict:
    """Stage 7: Collect performance data and generate cycle report.

    Note: In production, this node would be triggered 7 days after
    the last published piece, not immediately after publishing.
    The scheduler (or a delayed trigger) handles the timing.
    """

    cycle = state.cycle
    log.info("stage7_start", cycle_id=cycle.cycle_id)

    # ── Collect LinkedIn engagement ──
    # TODO: Pull from LinkedIn API / Buffer analytics
    # For each published LinkedIn draft:
    #   impressions, clicks, reactions, comments, shares
    linkedin_metrics = {}
    for draft in state.linkedin_drafts:
        if draft.published_url:
            # linkedin_api.get_share_statistics(draft.published_url)
            linkedin_metrics[draft.draft_id] = {
                "impressions": 0,
                "clicks": 0,
                "reactions": 0,
                "comments": 0,
                "shares": 0,
                "engagement_rate": 0.0,
            }

    # ── Collect email performance ──
    # TODO: Pull from HubSpot/Mailchimp
    email_metrics = {
        "open_rate": 0.0,
        "click_through_rate": 0.0,
        "unsubscribe_count": 0,
    }

    # ── Calculate topic performance scores ──
    topic_scores = {}
    for topic in state.shortlisted_topics:
        # Average engagement rate across all drafts for this topic
        topic_drafts = [
            d for d in state.linkedin_drafts if d.topic_id == topic.topic_id
        ]
        if topic_drafts:
            avg_engagement = sum(
                linkedin_metrics.get(d.draft_id, {}).get("engagement_rate", 0)
                for d in topic_drafts
            ) / len(topic_drafts)
            topic_scores[topic.topic_id] = avg_engagement

    # ── Generate performance report ──
    best_topic = max(topic_scores, key=topic_scores.get) if topic_scores else None
    best_topic_title = next(
        (t.title for t in state.shortlisted_topics if t.topic_id == best_topic), "N/A"
    )

    report = {
        "cycle_id": cycle.cycle_id,
        "linkedin_drafts_published": len([d for d in state.linkedin_drafts if d.published_at]),
        "blogs_published": len([d for d in state.blog_drafts if d.published_at]),
        "newsletter_sent": state.newsletter_draft.published_at is not None if state.newsletter_draft else False,
        "best_performing_topic": best_topic_title,
        "topic_scores": topic_scores,
        "email_metrics": email_metrics,
    }

    # TODO: Send performance report to Slack
    # Format as per spec section 7.6

    # TODO: Write topic performance scores back to Topic store
    # These will be loaded in the next cycle's Stage 2 for scoring boost/penalty

    log.info("stage7_complete", cycle_id=cycle.cycle_id)

    from datetime import datetime

    updated_cycle = cycle.model_copy(
        update={
            "status": CycleStatus.COMPLETE,
            "stage": 7,
            "completed_at": datetime.utcnow(),
        }
    )

    return {
        "performance_report": report,
        "cycle": updated_cycle,
    }
