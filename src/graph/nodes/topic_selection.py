"""Stage 2 -- Topic Selection Node (Parallel Per-Region).

Splits signals by region and runs 6 parallel LLM calls to produce
7-12 ranked topics per region. This avoids the problem of one massive
prompt overwhelmed by 200+ signals.

Architecture:
    signals (200+)
      ├── UK signals  → LLM ─┐
      ├── USA signals → LLM  │  asyncio.gather()
      ├── AU signals  → LLM  ├── all run simultaneously
      ├── CA signals  → LLM  │
      ├── EU signals  → LLM  │
      └── Global      → LLM ─┘
                              → merge → 38-65 topics

In dev mode: returns sample ranked topics.
"""

import asyncio
import json

import structlog

from src.graph.state import PipelineState
from src.models.enums import Region, StakeholderAudience, UrgencyLevel
from src.models.schemas import Topic
from src.settings import settings

log = structlog.get_logger()


# ── LLM output normalisation ──────────────────────────────────────────────
_URGENCY_MAP = {
    "breaking": UrgencyLevel.BREAKING,
    "high": UrgencyLevel.BREAKING,
    "urgent": UrgencyLevel.BREAKING,
    "critical": UrgencyLevel.BREAKING,
    "time-sensitive": UrgencyLevel.TIME_SENSITIVE,
    "time sensitive": UrgencyLevel.TIME_SENSITIVE,
    "timely": UrgencyLevel.TIME_SENSITIVE,
    "medium": UrgencyLevel.TIME_SENSITIVE,
    "moderate": UrgencyLevel.TIME_SENSITIVE,
    "evergreen": UrgencyLevel.EVERGREEN,
    "low": UrgencyLevel.EVERGREEN,
    "flexible": UrgencyLevel.EVERGREEN,
}

_REGION_MAP = {
    "uk": Region.UK,
    "united kingdom": Region.UK,
    "britain": Region.UK,
    "gb": Region.UK,
    "usa": Region.USA,
    "us": Region.USA,
    "united states": Region.USA,
    "america": Region.USA,
    "australia": Region.AUSTRALIA,
    "au": Region.AUSTRALIA,
    "canada": Region.CANADA,
    "ca": Region.CANADA,
    "europe": Region.EUROPE,
    "eu": Region.EUROPE,
    "european union": Region.EUROPE,
    "global": Region.GLOBAL,
    "international": Region.GLOBAL,
    "multi-region": Region.GLOBAL,
    "multi": Region.GLOBAL,
    "worldwide": Region.GLOBAL,
}

_STAKEHOLDER_MAP = {
    "supply": StakeholderAudience.SUPPLY,
    "supply partners": StakeholderAudience.SUPPLY,
    "supply partner": StakeholderAudience.SUPPLY,
    "pbsa": StakeholderAudience.SUPPLY,
    "operators": StakeholderAudience.SUPPLY,
    "property managers": StakeholderAudience.SUPPLY,
    "university": StakeholderAudience.UNIVERSITY,
    "universities": StakeholderAudience.UNIVERSITY,
    "higher education": StakeholderAudience.UNIVERSITY,
    "he": StakeholderAudience.UNIVERSITY,
    "hei": StakeholderAudience.UNIVERSITY,
    "hea": StakeholderAudience.HEA,
    "agents": StakeholderAudience.HEA,
    "education agents": StakeholderAudience.HEA,
    "counsellors": StakeholderAudience.HEA,
}


def _normalize_urgency(value) -> UrgencyLevel:
    if isinstance(value, UrgencyLevel):
        return value
    key = str(value or "").strip().lower()
    return _URGENCY_MAP.get(key, UrgencyLevel.TIME_SENSITIVE)


def _normalize_region(value) -> Region:
    if isinstance(value, Region):
        return value
    key = str(value or "").strip().lower()
    return _REGION_MAP.get(key, Region.GLOBAL)


def _normalize_stakeholder(value):
    if isinstance(value, StakeholderAudience):
        return value
    key = str(value or "").strip().lower()
    return _STAKEHOLDER_MAP.get(key)


def _to_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _truncate(text: str, max_len: int) -> str:
    text = str(text or "")
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


TOPIC_RULES_PATH = "config/topic-rules.json"
GUARDRAILS_PATH = "config/editorial-guardrails.json"
STAKEHOLDERS_PATH = "config/stakeholders.json"

# Per-region prompt — much simpler and more focused than the mega-prompt
REGION_TOPIC_PROMPT = """You are a topic selection editor for amber (international student accommodation sector).

You have {signal_count} signals from **{region}**. Extract **{target_min}-{target_max} distinct topics** for the weekly Amber Beat newsroom blog.

## Rules
- ONE signal = ONE topic (do NOT merge unless they are about the exact same event)
- Each topic must have a specific data point or fact
- Rank topics by importance (1 = most important)
- Apply the editorial filters: never cover domestic student news, party politics, or competitor brands

## Scoring Criteria
- Urgency (35%): Breaking = 10, Time-sensitive = 7, Evergreen = 3
- Regional relevance (25%): Multi-region = 10, Primary = 8, Secondary = 6
- Stakeholder fit (25%): All 3 audiences = 10, 2 = 7, 1 = 4
- Data quality (15%): Official/government = 10, Specialist = 7, General = 4

## Signals
{signals}

## Output
Return a JSON array of {target_min}-{target_max} topics:
[{{
    "title": "max 10 words",
    "summary": "3-4 sentences: key data + context + implication + what to watch",
    "rank": 1-{target_max},
    "urgency": "Breaking" | "Time-sensitive" | "Evergreen",
    "primary_region": "{region}",
    "secondary_regions": [],
    "stakeholder_tags": ["Supply", "University", "HEA"],
    "source_signal_indices": [0, 2],
    "rationale": "why this matters",
    "urgency_score": 0-10,
    "regional_relevance_score": 0-10,
    "stakeholder_fit_score": 0-10,
    "total_score": weighted total
}}]

Return ONLY the JSON array."""

REGION_ORDER = ["UK", "USA", "Australia", "Canada", "Europe", "Global"]
REGION_TARGETS = {
    "UK": (7, 12), "USA": (7, 12), "Australia": (7, 12),
    "Canada": (7, 12), "Europe": (7, 12), "Global": (3, 5),
}


async def select_topics(state: PipelineState) -> dict:
    """Stage 2: Parallel per-region topic selection.

    Splits signals by region and runs 6 simultaneous LLM calls,
    each producing 7-12 topics for its region.
    """

    cycle = state.cycle
    signals = state.signals
    errors: list[str] = []

    log.info("stage2_start", cycle_id=cycle.cycle_id, signal_count=len(signals))

    if not signals:
        errors.append("No signals to process -- Stage 1 produced no results")
        log.error("stage2_no_signals")
        return {"ranked_topics": [], "errors": errors}

    # -- Dev mode: return sample topics --
    if settings.dev_mode or not settings.is_llm_available:
        from src.sample_data import get_sample_topics
        ranked_topics = get_sample_topics(cycle.cycle_id, signals)
        log.info("stage2_complete_dev_mode", topic_count=len(ranked_topics))
        updated_cycle = cycle.model_copy(update={"stage": 3})
        return {"ranked_topics": ranked_topics, "cycle": updated_cycle, "errors": errors}

    # -- Production mode: parallel per-region calls --

    # 1. Group signals by region
    signals_by_region: dict[str, list] = {r: [] for r in REGION_ORDER}
    signal_index_map: dict[str, dict[int, int]] = {r: {} for r in REGION_ORDER}

    for global_idx, sig in enumerate(signals):
        region_key = sig.region.value if hasattr(sig.region, "value") else str(sig.region)
        if region_key not in signals_by_region:
            region_key = "Global"
        local_idx = len(signals_by_region[region_key])
        signal_index_map[region_key][local_idx] = global_idx
        signals_by_region[region_key].append(sig)

    # Log distribution
    for region in REGION_ORDER:
        count = len(signals_by_region[region])
        log.info("stage2_region_signals", region=region, count=count)

    # 2. Launch parallel LLM calls — one per region
    log.info("stage2_parallel_start", regions=len(REGION_ORDER))

    tasks = []
    for region in REGION_ORDER:
        region_signals = signals_by_region[region]
        if not region_signals:
            log.info("stage2_region_skip", region=region, reason="no signals")
            continue
        tasks.append(
            _rank_region(
                region=region,
                region_signals=region_signals,
                index_map=signal_index_map[region],
                all_signals=signals,
                cycle_id=cycle.cycle_id,
            )
        )

    # Run all regions simultaneously
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 3. Merge results
    all_topics: list[Topic] = []
    for result in results:
        if isinstance(result, Exception):
            errors.append(f"Region ranking failed: {result}")
            log.error("stage2_region_failed", error=str(result))
            continue
        region_topics, region_errors = result
        all_topics.extend(region_topics)
        errors.extend(region_errors)

    # 4. Sort by region order then rank within region
    region_sort = {r: i for i, r in enumerate(REGION_ORDER)}
    all_topics.sort(key=lambda t: (
        region_sort.get(t.primary_region.value if hasattr(t.primary_region, "value") else str(t.primary_region), 99),
        t.rank,
    ))

    # Re-assign global topic IDs
    for i, topic in enumerate(all_topics, 1):
        topic.topic_id = f"TOP-{i:02d}"

    log.info("stage2_complete", topic_count=len(all_topics), error_count=len(errors))

    # Log per-region counts
    for region in REGION_ORDER:
        count = sum(1 for t in all_topics
                    if (t.primary_region.value if hasattr(t.primary_region, "value") else str(t.primary_region)) == region)
        target = REGION_TARGETS.get(region, (7, 12))
        log.info("stage2_region_result", region=region, topics=count, target=f"{target[0]}-{target[1]}")

    updated_cycle = cycle.model_copy(update={"stage": 3})
    return {"ranked_topics": all_topics, "cycle": updated_cycle, "errors": errors}


async def _rank_region(
    region: str,
    region_signals: list,
    index_map: dict[int, int],
    all_signals: list,
    cycle_id: str,
) -> tuple[list[Topic], list[str]]:
    """Rank topics for a single region. Called in parallel."""

    errors: list[str] = []
    target_min, target_max = REGION_TARGETS.get(region, (7, 12))

    # Build signal list for the prompt
    signal_entries = []
    for i, sig in enumerate(region_signals):
        signal_entries.append({
            "index": i,
            "source": sig.source_name,
            "source_url": sig.source_url,
            "headline": sig.headline,
            "summary": sig.summary,
            "category": str(sig.topic_category),
            "is_negative": sig.is_negative_news,
            "is_opinion": getattr(sig, "is_opinion", False),
        })

    prompt = REGION_TOPIC_PROMPT.format(
        signal_count=len(signal_entries),
        region=region,
        target_min=target_min,
        target_max=target_max,
        signals=json.dumps(signal_entries, indent=2),
    )

    from src.llm import complete_json

    log.info("stage2_region_call", region=region, signals=len(signal_entries))

    try:
        raw_topics = await complete_json(
            role="editorial",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8000,
        )

        topics: list[Topic] = []
        for t in raw_topics:
            # Map local signal indices back to global indices
            source_ids = []
            source_urls = []
            for local_idx in t.get("source_signal_indices", []):
                global_idx = index_map.get(local_idx)
                if global_idx is not None and global_idx < len(all_signals):
                    sig = all_signals[global_idx]
                    source_ids.append(sig.signal_id or f"sig-{global_idx}")
                    if sig.source_url:
                        source_urls.append(sig.source_url)

            try:
                topic = Topic(
                    topic_id="",  # assigned after merge
                    cycle_id=cycle_id,
                    title=_truncate(t.get("title", "Untitled"), 80),
                    summary=t.get("summary", ""),
                    rank=max(1, min(target_max, int(t.get("rank", 1)))),
                    urgency=_normalize_urgency(t.get("urgency", "")),
                    primary_region=_normalize_region(region),
                    secondary_regions=[
                        _normalize_region(r) for r in t.get("secondary_regions", []) if r
                    ],
                    stakeholder_tags=[
                        _normalize_stakeholder(s)
                        for s in t.get("stakeholder_tags", [])
                        if _normalize_stakeholder(s) is not None
                    ],
                    source_signal_ids=source_ids,
                    source_urls=source_urls,
                    rationale=t.get("rationale", ""),
                    urgency_score=_to_float(t.get("urgency_score", 0)),
                    regional_relevance_score=_to_float(t.get("regional_relevance_score", 0)),
                    stakeholder_fit_score=_to_float(t.get("stakeholder_fit_score", 0)),
                    total_score=_to_float(t.get("total_score", 0)),
                )
                topics.append(topic)
            except Exception as topic_err:
                errors.append(f"[{region}] Topic skipped: {t.get('title', '?')} -- {topic_err}")

        # Sort by score within region
        topics.sort(key=lambda t: t.total_score, reverse=True)
        for i, topic in enumerate(topics, 1):
            topic.rank = i

        log.info("stage2_region_done", region=region, topics=len(topics))
        return topics, errors

    except Exception as e:
        errors.append(f"[{region}] Topic selection failed: {e}")
        log.error("stage2_region_error", region=region, error=str(e))
        return [], errors


def _load_json(path: str) -> dict:
    """Load a JSON config file."""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}
