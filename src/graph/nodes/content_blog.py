"""Stage 4B -- Blog Writer Agent.

Generates 3 blog posts from the top 3 topics, each through a different
stakeholder lens: Supply Partner, University, HEA/Agent.

In dev mode: returns sample blog posts.
"""

import json
import re
from pathlib import Path

import structlog

from src.graph.state import PipelineState
from src.models.enums import DraftChannel, DraftStatus, DraftVoice, StakeholderAudience
from src.models.schemas import ContentDraft
from src.settings import settings

log = structlog.get_logger()

BLOG_LENSES = [
    {
        "voice": DraftVoice.BLOG_SUPPLY,
        "audience": StakeholderAudience.SUPPLY,
        "label": "Supply Partner",
        "tone": "Operator language, data-forward, practical",
        "reader": "Property managers, PBSA operators, asset managers",
        "language": "yield, occupancy, void periods, bed-night revenue, covenant strength",
    },
    {
        "voice": DraftVoice.BLOG_UNIVERSITY,
        "audience": StakeholderAudience.UNIVERSITY,
        "label": "University / HE",
        "tone": "Policy-aware, strategic, finance-sensitive",
        "reader": "Housing team, Dean of Students, International Office, Finance Director",
        "language": "enrolment, student experience, compliance, partnerships, income diversification",
    },
    {
        "voice": DraftVoice.BLOG_HEA,
        "audience": StakeholderAudience.HEA,
        "label": "HEA / Education Agents",
        "tone": "Market intelligence, destination-focused, practical for advisors",
        "reader": "Senior education counsellors, franchise owners, frontline advisors",
        "language": "recruitment corridor, destination market, visa conversion, student pipeline",
    },
]


async def generate_blogs(state: PipelineState) -> dict:
    """Generate blog posts: top 3 per region from shortlisted topics.

    Each region's top 3 topics get a blog post through one of 3 stakeholder
    lenses (Supply, University, HEA), cycling through lenses per region.
    """

    cycle = state.cycle
    errors: list[str] = []

    # Pick top 3 per region from shortlisted topics (5 per region)
    region_order = ["UK", "USA", "Australia", "Canada", "Europe", "Global"]
    topics: list = []
    for region in region_order:
        region_topics = sorted(
            [t for t in state.shortlisted_topics
             if (t.primary_region.value if hasattr(t.primary_region, "value") else str(t.primary_region)) == region],
            key=lambda t: t.rank,
        )[:3]
        topics.extend(region_topics)

    log.info("stage4b_start", cycle_id=cycle.cycle_id, topic_count=len(topics))

    if len(topics) < 3:
        errors.append(f"Only {len(topics)} topics for blogs -- expected at least 3")

    # -- Dev mode: return sample blog posts --
    if settings.dev_mode or not settings.is_llm_available:
        from src.sample_data import get_sample_blog_draft
        assignments = _assign_topics_to_lenses_per_region(topics)
        drafts = []
        for lens, topic in assignments:
            draft = get_sample_blog_draft(topic, lens["audience"], lens["voice"], cycle.cycle_id)
            draft.validation_flags = _validate_blog(draft.content_body, draft.word_count)
            drafts.append(draft)
        log.info("stage4b_complete_dev_mode", draft_count=len(drafts))
        return {"blog_drafts": drafts, "errors": errors}

    # -- Production mode --
    assignments = _assign_topics_to_lenses_per_region(topics)
    drafts: list[ContentDraft] = []
    prompt_template = Path("prompts/blog-post.md").read_text()

    from src.llm import complete

    for lens, topic in assignments:
        generation_prompt = f"""{prompt_template}

## This Specific Blog

Topic: {topic.edited_title or topic.title}
Summary: {topic.edited_summary or topic.summary}
Content guidance: {topic.content_guidance}
Region: {topic.primary_region}
Source signals: {json.dumps(topic.source_signal_ids)}

## Audience Lens: {lens['label']}
Tone: {lens['tone']}
Reader: {lens['reader']}
Language to use: {lens['language']}

Write the full blog post now. Include H1, H2 sections, key stats callout, and CTA.
Mark key stats with [STAT] prefix for the callout box.
Target: 600-900 words."""

        try:
            content_body = await complete(
                role="generation",
                messages=[{"role": "user", "content": generation_prompt}],
                max_tokens=4000,
            )
            word_count = len(content_body.split())
            flags = _validate_blog(content_body, word_count)

            draft = ContentDraft(
                cycle_id=cycle.cycle_id,
                topic_id=topic.topic_id,
                channel=DraftChannel.BLOG,
                audience=lens["audience"],
                voice=lens["voice"],
                content_body=content_body,
                word_count=word_count,
                generation_prompt=generation_prompt,
                generation_model=settings.generation_model,
                status=DraftStatus.DRAFT,
                validation_flags=flags,
            )
            drafts.append(draft)

        except Exception as e:
            errors.append(f"Blog generation failed: {topic.title} / {lens['label']} -- {e}")
            log.error("blog_gen_failed", topic=topic.title, lens=lens["label"], error=str(e))

    log.info("stage4b_complete", draft_count=len(drafts))
    return {"blog_drafts": drafts, "errors": errors}


def _assign_topics_to_lenses_per_region(topics: list) -> list[tuple[dict, object]]:
    """Assign top 3 topics per region each to a stakeholder lens.

    For each region, the 3 topics cycle through the 3 lenses
    (Supply, University, HEA) in order.
    """
    region_order = ["UK", "USA", "Australia", "Canada", "Europe", "Global"]
    assignments = []

    for region in region_order:
        region_topics = [t for t in topics
                         if (t.primary_region.value if hasattr(t.primary_region, "value")
                             else str(t.primary_region)) == region]
        region_topics.sort(key=lambda t: t.rank)
        top3 = region_topics[:3]

        for i, topic in enumerate(top3):
            lens = BLOG_LENSES[i % len(BLOG_LENSES)]
            assignments.append((lens, topic))

    return assignments


def _assign_topics_to_lenses(topics: list) -> list[tuple[dict, object]]:
    """Legacy: assign 3 topics to 3 lenses (used if not per-region)."""
    assignments = []
    used_topic_ids = set()

    for lens in BLOG_LENSES:
        audience_key = lens["audience"].value

        best = None
        for topic in topics:
            if topic.topic_id in used_topic_ids:
                continue
            if audience_key in topic.stakeholder_tags:
                best = topic
                break

        if best is None:
            for topic in topics:
                if topic.topic_id not in used_topic_ids:
                    best = topic
                    break

        if best:
            assignments.append((lens, best))
            used_topic_ids.add(best.topic_id)

    return assignments


def _validate_blog(content: str, word_count: int) -> list[str]:
    """Validate blog against spec requirements."""
    flags = []

    if word_count < 600 or word_count > 900:
        flags.append(f"word_count_out_of_range ({word_count})")

    if "## " not in content and "# " not in content:
        flags.append("missing_headings")

    if not re.search(r'\d+[%.]?\d*', content):
        flags.append("missing_data_point")

    return flags
