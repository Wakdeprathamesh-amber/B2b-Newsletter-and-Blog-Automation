"""Stage 5 — Review Document Assembly.

Compiles all content into a single structured review document
and sends it to Google Docs + Slack notification.

Per spec:
- Waits for all content agents to complete
- Structured doc: Newsroom Blog → LinkedIn → Blogs → Newsletter
- Each draft shows: status, word count, validation flags, source topic
- Slack notification with summary + link + deadline
"""

import structlog

from src.graph.state import PipelineState
from src.models.enums import CycleStatus

log = structlog.get_logger()


async def assemble_review_doc(state: PipelineState) -> dict:
    """Compile all drafts into a review document and notify reviewers."""

    cycle = state.cycle
    linkedin = state.linkedin_drafts
    blogs = state.blog_drafts
    newsletter = state.newsletter_draft
    newsroom_items = state.newsroom_items or {}
    topics = state.shortlisted_topics

    all_drafts = linkedin + blogs + ([newsletter] if newsletter else [])
    newsroom_count = sum(len(v) for v in newsroom_items.values())
    total = len(all_drafts) + newsroom_count

    log.info("stage5_start", cycle_id=cycle.cycle_id, total_drafts=total)

    # ── Build the review document ──
    lines = [
        "AMBER CONTENT ENGINE — REVIEW DOCUMENT",
        f"Cycle: {cycle.cycle_id} | Generated: {cycle.started_at.isoformat()}",
        f"Total items: {total} (Newsroom: {newsroom_count}, LinkedIn: {len(linkedin)}, "
        f"Blogs: {len(blogs)}, Newsletter: {'1' if newsletter else '0'})",
        "",
        "HOW TO REVIEW:",
        "- Add comments directly to any draft",
        "- Use [APPROVED], [NEEDS EDIT], or [BLOCK] at the top of each section",
        "- When complete, click the Approve button or use the API",
        "",
        "=" * 60,
        "SECTION 1 — AMBER BEAT NEWSROOM BLOG ({} items)".format(newsroom_count),
        "=" * 60,
        "",
    ]

    # ── Newsroom Blog Items (weekly) ──
    region_order = ["UK", "USA", "Australia", "Canada", "Europe", "Global"]
    for region in region_order:
        items = newsroom_items.get(region, [])
        if not items:
            continue
        lines.append(f"── {region} ({len(items)} items) ──")
        lines.append("")
        for i, item in enumerate(items, 1):
            text = item.get("item_text", "")
            wc = item.get("word_count", len(text.split()))
            valid = "✓" if item.get("valid", True) else "⚠ LENGTH"
            lines.append(f"  {i}. {text}")
            lines.append(f"     [{wc}w {valid}] Source: {item.get('source_url', 'N/A')}")
            lines.append("")
        lines.append("-" * 40)
        lines.append("")

    lines.append("")
    lines.append("=" * 60)
    lines.append("SECTION 2 — LINKEDIN POSTS ({} drafts)".format(len(linkedin)))
    lines.append("=" * 60)
    lines.append("")

    # Group LinkedIn posts by topic
    topic_map = {t.topic_id: t for t in topics}
    current_topic = None

    for i, draft in enumerate(linkedin):
        topic = topic_map.get(draft.topic_id)
        topic_title = (topic.edited_title or topic.title) if topic else "Unknown"

        if draft.topic_id != current_topic:
            current_topic = draft.topic_id
            lines.append(f"\nTOPIC: {topic_title}")
            if topic:
                lines.append(f"Urgency: {topic.urgency} | Region: {topic.primary_region}")
            lines.append("")

        flags_str = f" ⚠ {', '.join(draft.validation_flags)}" if draft.validation_flags else ""
        lines.append(f"[{i+1}] {draft.voice} | {draft.status} | {draft.word_count} words{flags_str}")
        lines.append(draft.content_body)
        lines.append("")
        lines.append("-" * 40)

    lines.append("")
    lines.append("=" * 60)
    lines.append(f"SECTION 3 — BLOG POSTS ({len(blogs)} drafts)")
    lines.append("=" * 60)

    for i, draft in enumerate(blogs):
        topic = topic_map.get(draft.topic_id)
        topic_title = (topic.edited_title or topic.title) if topic else "Unknown"
        flags_str = f" ⚠ {', '.join(draft.validation_flags)}" if draft.validation_flags else ""

        lines.append(f"\n[Blog {i+1}] {draft.voice} — {topic_title}")
        lines.append(f"Audience: {draft.audience} | {draft.word_count} words{flags_str}")
        lines.append("")
        lines.append(draft.content_body)
        lines.append("")
        lines.append("-" * 40)

    lines.append("")
    lines.append("=" * 60)
    lines.append("SECTION 4 — NEWSLETTER (bimonthly, 1 draft)")
    lines.append("=" * 60)

    if newsletter:
        lines.append(f"\n{newsletter.word_count} words")
        if newsletter.validation_flags:
            lines.append(f"⚠ {', '.join(newsletter.validation_flags)}")
        lines.append("")
        lines.append(newsletter.content_body)
    else:
        lines.append("\n[Newsletter generation failed — see error log]")

    lines.append("")
    lines.append("=" * 60)
    lines.append("[ APPROVE ALL AND SEND TO PUBLISH ]")
    lines.append("=" * 60)

    review_doc_content = "\n".join(lines)

    # TODO: Write to Google Docs via google-api-python-client
    # doc_url = google_docs_client.create_document(
    #     title=f"Amber Review — {cycle.cycle_id}",
    #     content=review_doc_content,
    # )
    doc_url = f"https://docs.google.com/document/d/placeholder-{cycle.cycle_id}"

    # TODO: Send Slack notification
    # slack_message = (
    #     f"*Content cycle {cycle.cycle_id} is ready for review*\n"
    #     f"• {len(linkedin)} LinkedIn posts\n"
    #     f"• {len(blogs)} blog posts\n"
    #     f"• {'1 newsletter' if newsletter else '0 newsletters'}\n"
    #     f"• Review deadline: 48 hours\n"
    #     f"• <{doc_url}|Open review document>"
    # )

    log.info("stage5_complete", doc_url=doc_url, total_drafts=total)

    updated_cycle = cycle.model_copy(
        update={"stage": 5, "draft_count": total}
    )

    return {
        "review_doc_url": doc_url,
        "cycle": updated_cycle,
    }
