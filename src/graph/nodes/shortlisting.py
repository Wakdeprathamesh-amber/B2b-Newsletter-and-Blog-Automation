"""Stage 3 -- Shortlisting Node (Parallel Per-Region).

Takes the 7-12 ranked topics per region and selects the top 5 per region
using parallel LLM calls. These shortlisted topics feed LinkedIn, Blog,
and Newsletter generation.

Architecture:
    ranked topics (38-65)
      ├── UK topics (7-12)  → LLM → top 5 ─┐
      ├── USA topics        → LLM → top 5   │  asyncio.gather()
      ├── AU topics         → LLM → top 5   ├── all run simultaneously
      ├── CA topics         → LLM → top 5   │
      ├── EU topics         → LLM → top 5   │
      └── Global topics     → LLM → top 3  ─┘
                                             → merge → 28 shortlisted

In dev mode: returns sample shortlisted topics.
"""

import asyncio
import json

import structlog

from src.graph.state import PipelineState
from src.models.schemas import Topic
from src.settings import settings

log = structlog.get_logger()

REGION_ORDER = ["UK", "USA", "Australia", "Canada", "Europe", "Global"]
REGION_SHORTLIST_TARGETS = {
    "UK": 5, "USA": 5, "Australia": 5, "Canada": 5, "Europe": 5, "Global": 3,
}

REGION_SHORTLIST_PROMPT = """You are a shortlisting editor for amber. From these {topic_count} ranked topics for **{region}**, select the **top {target}** for LinkedIn posts, blog articles, and newsletter content.

## Selection Rules
1. Pick the {target} most impactful/urgent topics
2. Ensure variety — not all from same category
3. At least 1 topic should be relevant to each stakeholder group (Supply, University, HEA) if possible
4. Prefer topics with strong data points
5. Each topic must work for at least 2 channels (LinkedIn, Blog, Newsletter)

## Ranked Topics for {region}
{topics}

## For Each Selected Topic, Provide:
- rank: 1-{target} (1 = top priority)
- title: may refine for clarity
- summary: 3-4 sentences with key data points — self-contained and fact-rich
- primary_region: "{region}"
- secondary_regions: []
- stakeholder_tags: which audiences this serves
- content_guidance: 1-2 sentences of editorial direction for content agents

Return a JSON array of exactly {target} topic objects.
Return ONLY the JSON array."""


async def shortlist_topics(state: PipelineState) -> dict:
    """Stage 3: Parallel per-region shortlisting — top 5 per region."""

    cycle = state.cycle
    ranked_topics = state.ranked_topics
    errors: list[str] = []

    log.info("stage3_start", cycle_id=cycle.cycle_id, candidate_count=len(ranked_topics))

    if len(ranked_topics) < 5:
        errors.append(f"Only {len(ranked_topics)} ranked topics — proceeding with fewer")
        log.warning("stage3_low_topics", count=len(ranked_topics))

    # -- Dev mode --
    if settings.dev_mode or not settings.is_llm_available:
        from src.sample_data import get_sample_shortlisted_topics
        shortlisted = get_sample_shortlisted_topics(cycle.cycle_id, state.signals)
        log.info("stage3_complete_dev_mode", shortlisted_count=len(shortlisted))
        updated_cycle = cycle.model_copy(
            update={"stage": 3, "topic_count": len(shortlisted)}
        )
        return {
            "shortlisted_topics": shortlisted,
            "ranked_topics": ranked_topics,
            "cycle": updated_cycle,
            "errors": errors,
        }

    # -- Production mode: parallel per-region calls --

    # Group ranked topics by region
    topics_by_region: dict[str, list[Topic]] = {r: [] for r in REGION_ORDER}
    for t in ranked_topics:
        region_key = t.primary_region.value if hasattr(t.primary_region, "value") else str(t.primary_region)
        if region_key in topics_by_region:
            topics_by_region[region_key].append(t)
        else:
            topics_by_region["Global"].append(t)

    # Launch parallel LLM calls
    log.info("stage3_parallel_start", regions=len(REGION_ORDER))
    tasks = []
    for region in REGION_ORDER:
        region_topics = topics_by_region[region]
        if not region_topics:
            log.info("stage3_region_skip", region=region, reason="no ranked topics")
            continue
        tasks.append(_shortlist_region(region, region_topics, ranked_topics, cycle.cycle_id))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Merge
    all_shortlisted: list[Topic] = []
    for result in results:
        if isinstance(result, Exception):
            errors.append(f"Region shortlisting failed: {result}")
            log.error("stage3_region_failed", error=str(result))
            continue
        region_topics, region_errors = result
        all_shortlisted.extend(region_topics)
        errors.extend(region_errors)

    # Sort by region order then rank
    region_sort = {r: i for i, r in enumerate(REGION_ORDER)}
    all_shortlisted.sort(key=lambda t: (
        region_sort.get(t.primary_region.value if hasattr(t.primary_region, "value") else str(t.primary_region), 99),
        t.rank,
    ))

    log.info("stage3_complete", shortlisted_count=len(all_shortlisted))

    for region in REGION_ORDER:
        count = sum(1 for t in all_shortlisted
                    if (t.primary_region.value if hasattr(t.primary_region, "value") else str(t.primary_region)) == region)
        target = REGION_SHORTLIST_TARGETS.get(region, 5)
        log.info("stage3_region_result", region=region, shortlisted=count, target=target)

    updated_cycle = cycle.model_copy(
        update={"stage": 3, "topic_count": len(all_shortlisted)}
    )
    return {
        "shortlisted_topics": all_shortlisted,
        "ranked_topics": ranked_topics,
        "cycle": updated_cycle,
        "errors": errors,
    }


async def _shortlist_region(
    region: str,
    region_topics: list[Topic],
    all_ranked: list[Topic],
    cycle_id: str,
) -> tuple[list[Topic], list[str]]:
    """Shortlist topics for a single region. Called in parallel."""

    errors: list[str] = []
    target = REGION_SHORTLIST_TARGETS.get(region, 5)

    # If we have fewer or equal to target, just take all
    if len(region_topics) <= target:
        for i, t in enumerate(region_topics, 1):
            t.content_guidance = t.content_guidance or t.rationale
        log.info("stage3_region_auto", region=region, count=len(region_topics), reason="at or below target")
        return region_topics, errors

    # Build topic data for the prompt
    topic_data = [
        {
            "rank": t.rank,
            "title": t.title,
            "summary": t.summary,
            "urgency": str(t.urgency),
            "stakeholder_tags": [str(a) for a in (t.stakeholder_tags or [])],
            "total_score": t.total_score,
            "rationale": t.rationale,
        }
        for t in region_topics
    ]

    prompt = REGION_SHORTLIST_PROMPT.format(
        topic_count=len(region_topics),
        region=region,
        target=target,
        topics=json.dumps(topic_data, indent=2),
    )

    from src.llm import complete_json
    from src.graph.nodes.topic_selection import (
        _normalize_region, _normalize_stakeholder, _normalize_urgency, _truncate,
    )

    log.info("stage3_region_call", region=region, candidates=len(region_topics), target=target)

    try:
        raw_shortlist = await complete_json(
            role="editorial",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
        )

        shortlisted: list[Topic] = []
        for t in raw_shortlist:
            # Match back to original ranked topic for source_urls etc.
            shortlist_title = t.get("title", "").strip().lower()
            original = next(
                (rt for rt in region_topics if rt.title.strip().lower() == shortlist_title),
                None,
            )
            if original is None:
                # Fuzzy match
                shortlist_words = set(shortlist_title.split())
                best_match, best_overlap = None, 0
                for rt in region_topics:
                    rt_words = set(rt.title.strip().lower().split())
                    overlap = len(shortlist_words & rt_words)
                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_match = rt
                if best_match and best_overlap >= 2:
                    original = best_match

            try:
                topic = Topic(
                    topic_id=original.topic_id if original else "",
                    cycle_id=cycle_id,
                    title=_truncate(t.get("title", "Untitled"), 80),
                    summary=t.get("summary", ""),
                    rank=max(1, min(target, int(t.get("rank", 1)))),
                    urgency=_normalize_urgency(t.get("urgency", "Evergreen")),
                    primary_region=_normalize_region(region),
                    secondary_regions=[
                        _normalize_region(r) for r in t.get("secondary_regions", []) if r
                    ],
                    stakeholder_tags=[
                        _normalize_stakeholder(s)
                        for s in t.get("stakeholder_tags", [])
                        if _normalize_stakeholder(s) is not None
                    ],
                    source_signal_ids=original.source_signal_ids if original else [],
                    source_urls=original.source_urls if original else [],
                    rationale=original.rationale if original else "",
                    content_guidance=t.get("content_guidance", ""),
                    urgency_score=original.urgency_score if original else 0,
                    regional_relevance_score=original.regional_relevance_score if original else 0,
                    stakeholder_fit_score=original.stakeholder_fit_score if original else 0,
                    total_score=original.total_score if original else 0,
                )
                shortlisted.append(topic)
            except Exception as topic_err:
                errors.append(f"[{region}] Shortlist skipped: {t.get('title', '?')} -- {topic_err}")

        shortlisted.sort(key=lambda t: t.rank)
        log.info("stage3_region_done", region=region, shortlisted=len(shortlisted))
        return shortlisted, errors

    except Exception as e:
        errors.append(f"[{region}] Shortlisting failed: {e}")
        log.error("stage3_region_error", region=region, error=str(e))
        return [], errors
