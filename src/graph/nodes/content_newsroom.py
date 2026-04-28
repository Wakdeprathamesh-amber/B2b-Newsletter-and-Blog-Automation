"""Stage 4D -- Amber Beat Newsroom Blog Agent (Weekly).

Generates 7-12 short news items per region for the weekly Amber Beat
newsroom blog. Each item is 21-25 words, neutral tone, data-led,
ending with a (Source) hyperlink.

Regions in fixed order: UK → USA → Australia → Canada → Europe → Global.
Within each region, items are ordered by topic priority:
  1. Policy & regulatory shifts
  2. Intl student enrolment / demand
  3. University-related
  4. PBSA supply & investment

In dev mode: returns sample newsroom items.
"""

import json
from pathlib import Path

import structlog

from src.graph.state import PipelineState
from src.models.enums import Region
from src.models.schemas import Topic
from src.settings import settings

log = structlog.get_logger()

# Topic priority ordering for within-region sorting
TOPIC_PRIORITY = {
    "Policy Changes": 1,
    "Visa Data": 1,
    "Student Demand": 2,
    "Emerging Markets": 2,
    "QS Rankings": 3,
    "Rent Trends": 4,
    "Supply Outlook": 4,
    "Other": 5,
}

REGION_ORDER = [Region.UK, Region.USA, Region.AUSTRALIA, Region.CANADA, Region.EUROPE, Region.GLOBAL]

NEWSROOM_PROMPT = """You are a newsroom editor for **amber Beat**, a weekly student accommodation sector news roundup published at amberstudent.com/news/amberbeat.

Your job: convert the ranked topics below into concise newsroom blog items — one item per topic.

## Item Format Rules
- Each item: **one sentence, 20-30 words**, neutral factual tone.
- Include at least one specific data point (number, percentage, monetary figure) where available.
- End each item with source attribution in brackets: [Source](url)
- No opinion, no "amber thinks", no promotional language.
- Factual, scannable, single-sentence format.

## Topic Priority Order (within each region)
1. Policy & regulatory shifts (visa, caps, immigration)
2. International student enrolment / demand (applications, visa issuance, YoY)
3. University-related (rankings, funding, campus changes)
4. PBSA supply & investment (M&A, new developments, bed counts)

## Real Examples (from published amber Beat — match this style exactly):
- UK international enrollments declined 31% year-over-year, with 70% of universities reporting postgraduate decreases due to visa restrictions. [Source](url)
- Tiger Developments commenced a £40M, 172-bed PBSA project near University of Manchester, targeting 2027/28 completion. [Source](url)
- Student visa rejections for Indian applicants increased to 61% (from 53%), significantly exceeding European rejection rates (~9%). [Source](url)
- Tallahassee began construction on a $100M, 804-bed student housing complex near Florida State University, targeting 2028 completion. [Source](url)
- Scape expanded to $20B PBSA operator managing approximately 20,000 apartments across 40 properties, targeting 100,000 beds by 2030/32. [Source](url)
- Study permits declined 64% amid tightening policies, with Indian visa refusals surging significantly. [Source](url)
- Germany is approaching 420,000 international students, driven by student intake restrictions elsewhere. [Source](url)
- Greystar acquired two student housing assets in Salamanca and Valencia from Straco, adding 1,600 beds. [Source](url)

## Topics by Region

{regional_topics}

## Output Format
Return a JSON object with region keys, each containing an array of items:
{{
    "UK": [
        {{"item_text": "21-25 word news item ending with (Source)", "topic_id": "top-001", "source_url": "https://..."}},
        ...
    ],
    "USA": [...],
    "Australia": [...],
    "Canada": [...],
    "Europe": [...],
    "Global": [...]
}}

Target: 7-12 items per region (fewer for Global: 3-5).
Return ONLY the JSON object."""


async def generate_newsroom_blog(state: PipelineState) -> dict:
    """Generate Amber Beat newsroom blog items: 7-12 per region, 21-25 words each."""

    cycle = state.cycle
    # Newsroom blog uses RANKED topics (7-12 per region), not shortlisted (5 per region)
    topics = state.ranked_topics
    errors: list[str] = []

    log.info("stage4d_start", cycle_id=cycle.cycle_id, topic_count=len(topics))

    # -- Dev mode: return sample newsroom items --
    if settings.dev_mode or not settings.is_llm_available:
        from src.sample_data import get_sample_newsroom_items
        items = get_sample_newsroom_items(cycle.cycle_id, topics)
        log.info("stage4d_complete_dev_mode", item_count=sum(len(v) for v in items.values()))
        return {"newsroom_items": items, "errors": errors}

    # -- Production mode --
    # Group topics by region and sort by topic priority within each
    regional_topics: dict[str, list[dict]] = {}
    for region in REGION_ORDER:
        region_key = region.value
        region_topics = [t for t in topics if t.primary_region == region]
        # Sort by topic priority
        region_topics.sort(key=lambda t: _topic_priority(t))
        regional_topics[region_key] = [
            {
                "topic_id": t.topic_id,
                "title": t.edited_title or t.title,
                "summary": t.edited_summary or t.summary,
                "source_urls": t.source_urls[:2] if t.source_urls else [],
                "category": "",  # Topic model doesn't carry category; inferred from signals
                "stakeholders": [str(s) for s in (t.stakeholder_tags or [])],
            }
            for t in region_topics
        ]

    prompt = NEWSROOM_PROMPT.format(
        regional_topics=json.dumps(regional_topics, indent=2)
    )

    from src.llm import complete_json

    try:
        raw_items = await complete_json(
            role="generation",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8000,
        )

        # Validate and structure the output
        newsroom_items: dict[str, list[dict]] = {}
        for region in ["UK", "USA", "Australia", "Canada", "Europe", "Global"]:
            region_items = raw_items.get(region, [])
            validated = []
            for item in region_items:
                text = item.get("item_text", "")
                word_count = len(text.split())
                validated.append({
                    "item_text": text,
                    "topic_id": item.get("topic_id", ""),
                    "source_url": item.get("source_url", ""),
                    "word_count": word_count,
                    "valid": 18 <= word_count <= 28,  # slight tolerance
                })
            newsroom_items[region] = validated

        total = sum(len(v) for v in newsroom_items.values())
        log.info("stage4d_complete", item_count=total)
        return {"newsroom_items": newsroom_items, "errors": errors}

    except Exception as e:
        errors.append(f"Newsroom blog generation failed: {e}")
        log.error("newsroom_gen_failed", error=str(e))
        return {"newsroom_items": {}, "errors": errors}


def _topic_priority(topic: Topic) -> int:
    """Return sort priority based on urgency and title keywords (lower = higher priority).

    Priority order per Amber Beat spec:
      1. Policy & regulatory shifts (visa, caps, immigration)
      2. Intl student enrolment / demand
      3. University-related (rankings, funding)
      4. PBSA supply & investment
    """
    # Breaking urgency always goes to top
    if hasattr(topic, "urgency") and str(topic.urgency) == "Breaking":
        return 0

    # Infer category from title/summary keywords since Topic doesn't carry topic_category
    text = (topic.title + " " + topic.summary).lower()
    if any(kw in text for kw in ["visa", "policy", "cap", "immigration", "regulation", "route", "mac"]):
        return 1
    if any(kw in text for kw in ["enrolment", "enrollment", "demand", "application", "student number", "cohort", "mobility"]):
        return 2
    if any(kw in text for kw in ["ranking", "university", "qs", "russell group", "ofs", "financial distress"]):
        return 3
    if any(kw in text for kw in ["rent", "pbsa", "supply", "investment", "yield", "bed", "pipeline", "housing"]):
        return 4
    return 5
