"""Human Gate 1 — Topic Approval.

This is the first human checkpoint. The pipeline pauses here until a human
approves, edits, swaps, or rejects topics.

Uses LangGraph's interrupt() to pause the graph. The state is checkpointed,
and the graph resumes when the FastAPI endpoint calls graph.update_state()
with the reviewer's decisions.

Per spec:
- Reviewer can: approve all, approve with edits, swap topics, reject topics, pause cycle
- Timeout: 12h reminder, 24h escalation, 48h auto-pause
- All decisions logged in ReviewSession
"""

import structlog
from langgraph.types import interrupt

from src.graph.state import PipelineState
from src.models.enums import CycleStatus, TopicStatus
from src.models.schemas import ReviewSession

log = structlog.get_logger()


async def gate1_notify(state: PipelineState) -> dict:
    """Send Slack notification with topic approval brief.

    This runs BEFORE the interrupt — it sends the notification,
    then the next node (gate1_wait) pauses the graph.
    """
    cycle = state.cycle
    shortlisted = state.shortlisted_topics
    ranked = state.ranked_topics

    log.info("gate1_notify", cycle_id=cycle.cycle_id, topic_count=len(shortlisted))

    # Build the approval brief
    brief_lines = [
        f"*Amber Content Engine — Topic Approval*",
        f"Cycle: `{cycle.cycle_id}` | Signals captured: {cycle.signal_count}",
        f"",
        f"*Top 5 Topics for This Cycle:*",
    ]

    for topic in shortlisted:
        brief_lines.append(
            f"\n*#{topic.rank}: {topic.title}*\n"
            f"  Urgency: {topic.urgency} | Region: {topic.primary_region} | "
            f"Audiences: {', '.join(topic.stakeholder_tags)}\n"
            f"  {topic.summary}\n"
            f"  _Guidance: {topic.content_guidance}_"
        )

    if len(ranked) > 5:
        brief_lines.append(f"\n_Longlist ({len(ranked) - 5} additional topics available for swap)_")

    brief = "\n".join(brief_lines)

    # TODO: Send to Slack via slack_sdk
    # slack_client.chat_postMessage(
    #     channel=settings.slack_review_channel,
    #     text=brief,
    #     blocks=[...interactive blocks with approve/edit/swap buttons...]
    # )

    log.info("gate1_notification_sent", cycle_id=cycle.cycle_id)

    updated_cycle = cycle.model_copy(update={"status": CycleStatus.AWAITING_TOPIC_APPROVAL})
    return {"cycle": updated_cycle}


async def gate1_wait(state: PipelineState) -> dict:
    """Pause the pipeline and wait for human approval.

    LangGraph's interrupt() checkpoints the state and halts execution.
    The graph resumes when the FastAPI endpoint calls:
        graph.update_state(thread_id, {"gate1_approved": True, ...})
        graph.invoke(None, {"configurable": {"thread_id": thread_id}})

    The interrupt value is what the human provides when resuming.
    """
    cycle = state.cycle
    log.info("gate1_waiting", cycle_id=cycle.cycle_id)

    # This pauses the graph. The human's response comes back as the return value.
    human_response = interrupt(
        {
            "gate": "topic_approval",
            "cycle_id": cycle.cycle_id,
            "message": "Waiting for topic approval. Use the API to approve, edit, swap, or reject topics.",
            "topics": [t.model_dump() for t in state.shortlisted_topics],
        }
    )

    # ── Process the human's response ──
    # human_response is a dict with the reviewer's decisions, provided via
    # graph.invoke(Command(resume=response_data))

    action = human_response.get("action", "approve_all")
    reviewer = human_response.get("reviewer_name", "unknown")
    decisions = human_response.get("decisions", [])

    session = ReviewSession(
        cycle_id=cycle.cycle_id,
        gate="TopicApproval",
        reviewer_name=reviewer,
        decisions=decisions,
    )

    if action == "pause":
        log.info("gate1_paused", reviewer=reviewer)
        updated_cycle = cycle.model_copy(update={"status": CycleStatus.CANCELLED})
        return {"cycle": updated_cycle, "gate1_session": session, "gate1_approved": False}

    # Apply edits/swaps/rejections to the shortlisted topics
    updated_topics = list(state.shortlisted_topics)

    for decision in decisions:
        topic_idx = next(
            (i for i, t in enumerate(updated_topics) if t.topic_id == decision.get("item_id")),
            None,
        )
        if topic_idx is None:
            continue

        if decision.get("action") == "edit":
            topic = updated_topics[topic_idx]
            topic.edited_title = decision.get("edited_title")
            topic.edited_summary = decision.get("edited_summary")
            topic.status = TopicStatus.EDITED
            topic.approved_by = reviewer

        elif decision.get("action") == "reject":
            updated_topics[topic_idx].status = TopicStatus.REJECTED
            # Promote next from longlist if available
            longlist_candidates = [
                t for t in state.ranked_topics
                if t.rank > 5 and t.title not in [ut.title for ut in updated_topics]
            ]
            if longlist_candidates:
                replacement = longlist_candidates[0]
                replacement.rank = updated_topics[topic_idx].rank
                updated_topics[topic_idx] = replacement

        elif decision.get("action") == "swap":
            swap_id = decision.get("swapped_with")
            replacement = next(
                (t for t in state.ranked_topics if t.topic_id == swap_id), None
            )
            if replacement:
                replacement.rank = updated_topics[topic_idx].rank
                updated_topics[topic_idx] = replacement

    # Mark all remaining as approved
    for topic in updated_topics:
        if topic.status == TopicStatus.PENDING:
            topic.status = TopicStatus.APPROVED
            topic.approved_by = reviewer

    # Filter out rejected
    approved_topics = [t for t in updated_topics if t.status != TopicStatus.REJECTED]

    from datetime import datetime

    updated_cycle = cycle.model_copy(
        update={
            "status": CycleStatus.RUNNING,
            "stage": 4,
            "topics_approved_at": datetime.utcnow(),
            "topic_count": len(approved_topics),
        }
    )

    log.info("gate1_approved", reviewer=reviewer, topic_count=len(approved_topics))

    return {
        "shortlisted_topics": approved_topics,
        "cycle": updated_cycle,
        "gate1_approved": True,
        "gate1_session": session,
    }
