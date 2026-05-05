"""Helper module for reading topics from Google Sheets with validation."""

import structlog
from src.models.schemas import Topic
from src.models.enums import Region, UrgencyLevel, StakeholderAudience

log = structlog.get_logger()

RMAP = {
    "uk": Region.UK,
    "usa": Region.USA,
    "us": Region.USA,
    "australia": Region.AUSTRALIA,
    "canada": Region.CANADA,
    "europe": Region.EUROPE,
    "global": Region.GLOBAL,
}

AMAP = {
    "supply": StakeholderAudience.SUPPLY,
    "supply partner": StakeholderAudience.SUPPLY,
    "supply partners": StakeholderAudience.SUPPLY,
    "university": StakeholderAudience.UNIVERSITY,
    "universities": StakeholderAudience.UNIVERSITY,
    "he": StakeholderAudience.UNIVERSITY,
    "hea": StakeholderAudience.HEA,
    "agents": StakeholderAudience.HEA,
    "education agents": StakeholderAudience.HEA,
}


def read_ranked_topics(
    sheets,
    approved_only: bool = True,
    channel_filter: str | None = None,
) -> list[Topic]:
    """Read topics from Ranked Topics tab with validation.
    
    Args:
        sheets: SheetsClient instance
        approved_only: Only return approved topics
        channel_filter: Filter by channel (e.g., "Newsroom", "LinkedIn")
    
    Returns:
        List of Topic objects
    """
    ws = sheets._ws("Ranked Topics")
    data = ws.get_all_values()
    
    if len(data) < 2:
        log.warning("ranked_topics_empty")
        return []

    headers = data[0]
    col = {h: i for i, h in enumerate(headers)}
    topics = []

    def g(row, name):
        """Get column value safely."""
        idx = col.get(name)
        if idx is None or idx >= len(row):
            return ""
        return row[idx].strip()

    for row_idx, row in enumerate(data[1:], start=2):
        try:
            # Check decision filter
            if approved_only:
                decision = g(row, "decision").lower()
                if decision not in ("approve", "approved", "edit"):
                    continue

            # Check channel filter
            if channel_filter:
                channels = g(row, "channels").lower()
                if channel_filter.lower() not in channels:
                    continue

            # Parse region
            region_str = g(row, "primary_region").lower()
            region = RMAP.get(region_str, Region.GLOBAL)

            # Parse stakeholder tags
            tags_str = g(row, "stakeholder_tags")
            tags = []
            for tag in tags_str.split(","):
                tag_clean = tag.strip().lower()
                if tag_clean in AMAP:
                    tags.append(AMAP[tag_clean])

            # Parse rank
            try:
                rank = int(g(row, "rank"))
            except ValueError:
                rank = 99

            # Parse urgency
            urgency_str = g(row, "urgency").lower()
            urgency_map = {
                "breaking": UrgencyLevel.BREAKING,
                "time-sensitive": UrgencyLevel.TIME_SENSITIVE,
                "time sensitive": UrgencyLevel.TIME_SENSITIVE,
                "evergreen": UrgencyLevel.EVERGREEN,
            }
            urgency = urgency_map.get(urgency_str, UrgencyLevel.TIME_SENSITIVE)

            # Build topic
            topic = Topic(
                topic_id=g(row, "topic_id") or f"t-{len(topics)+1}",
                title=g(row, "edited_title") or g(row, "title"),
                summary=g(row, "edited_summary") or g(row, "summary"),
                content_guidance=g(row, "content_guidance") or g(row, "reviewer_notes"),
                rank=min(rank, 60),
                urgency=urgency,
                primary_region=region,
                stakeholder_tags=tags,
                source_urls=[
                    u.strip()
                    for u in g(row, "source_references").split("\n")
                    if u.strip()
                ],
            )

            # Attach voice/lens as extra attributes for downstream use
            topic._linkedin_voice = g(row, "linkedin_voice")
            topic._blog_lens = g(row, "blog_lens")
            topic._channels = g(row, "channels")

            topics.append(topic)

        except Exception as e:
            log.error(
                "topic_parse_error",
                row=row_idx,
                error=str(e),
                topic_id=g(row, "topic_id"),
            )
            continue

    log.info(
        "topics_loaded",
        total=len(topics),
        approved_only=approved_only,
        channel_filter=channel_filter,
    )
    
    return topics


def validate_topics_for_generation(
    topics: list[Topic],
    channel: str,
    max_topics: int = 50,
) -> list[str]:
    """Validate topics before content generation.
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if not topics:
        errors.append(f"No topics tagged for {channel}")
        return errors

    if len(topics) > max_topics:
        errors.append(
            f"Too many topics ({len(topics)}). Max {max_topics} per generation. "
            f"Consider splitting into multiple batches."
        )

    for topic in topics:
        # Check title
        if not topic.title or len(topic.title) < 10:
            errors.append(
                f"Topic {topic.topic_id}: title too short ({len(topic.title)} chars, min 10)"
            )

        # Check summary
        if not topic.summary or len(topic.summary) < 50:
            errors.append(
                f"Topic {topic.topic_id}: summary too short ({len(topic.summary)} chars, min 50)"
            )

        # Check source URLs
        if not topic.source_urls:
            errors.append(f"Topic {topic.topic_id}: no source URLs")

    return errors
