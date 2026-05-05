"""Shared reader for approved topics from the Ranked Topics sheet."""

from __future__ import annotations

from src.models.enums import Region, StakeholderAudience, UrgencyLevel
from src.models.schemas import Topic
from src.integrations.sheet_contracts import ensure_ranked_topics_contract

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
    "university": StakeholderAudience.UNIVERSITY,
    "hea": StakeholderAudience.HEA,
}


def read_ranked_topics(
    sheets,
    *,
    approved_only: bool = False,
    channel_filter: str | None = None,
) -> list[Topic]:
    """Read topics from Ranked Topics tab with optional approval/channel filters."""
    ensure_ranked_topics_contract(sheets)
    ws = sheets._ws("Ranked Topics")
    data = ws.get_all_values()
    if len(data) < 2:
        return []

    headers = data[0]
    col = {h: i for i, h in enumerate(headers)}
    topics: list[Topic] = []

    def g(row: list[str], name: str) -> str:
        idx = col.get(name)
        if idx is None or idx >= len(row):
            return ""
        return row[idx].strip()

    for row in data[1:]:
        decision = g(row, "decision").lower()
        channels = g(row, "channels").lower()

        if approved_only and decision not in ("approve", "approved", "edit"):
            continue
        if channel_filter and channel_filter.lower() not in channels:
            continue

        region = RMAP.get(g(row, "primary_region").lower(), Region.GLOBAL)
        tags = [
            AMAP[t.strip().lower()]
            for t in g(row, "stakeholder_tags").split(",")
            if t.strip().lower() in AMAP
        ]
        try:
            rank = int(g(row, "rank"))
        except ValueError:
            rank = 99

        topic = Topic(
            topic_id=g(row, "topic_id") or f"t-{len(topics) + 1}",
            title=g(row, "edited_title") or g(row, "title"),
            summary=g(row, "edited_summary") or g(row, "summary"),
            content_guidance=g(row, "content_guidance") or g(row, "reviewer_notes"),
            rank=min(rank, 60),
            urgency=UrgencyLevel.TIME_SENSITIVE,
            primary_region=region,
            stakeholder_tags=tags,
            source_urls=[u.strip() for u in g(row, "source_references").split("\n") if u.strip()],
        )
        topics.append(topic)

    return topics
