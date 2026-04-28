"""Stage 4C -- Newsletter Agent (Bimonthly).

Generates 2 newsletter variants (Market Watch + amber Beat) by
**cherry-picking the best items from the weekly Amber Beat newsroom blog**.

The newsletter does NOT generate new content — it curates from the
newsroom_items that were already produced by the newsroom blog node.

Cadence: bimonthly (every 2 months).
Source: newsroom_items dict (region → list of 21-25 word news items).

Structure per variant:
- Editor's Choice (2-3 items spanning 2+ regions)
- Top Global News (8 items: 2 per region — UK, US, Australia, Europe)
- Audience-specific CTA

In dev mode: returns sample newsletters.
"""

import json
from pathlib import Path

import structlog

from src.graph.state import PipelineState
from src.models.enums import DraftChannel, DraftStatus, DraftVoice, Region
from src.models.schemas import ContentDraft
from src.settings import settings

log = structlog.get_logger()


async def generate_newsletter(state: PipelineState) -> dict:
    """Generate bimonthly newsletter by curating from newsroom blog items.

    Sources from state.newsroom_items (produced by the newsroom blog node).
    Does NOT generate fresh content — selects and formats the best items.
    """

    cycle = state.cycle
    newsroom_items = state.newsroom_items or {}
    errors: list[str] = []

    log.info("stage4c_start", cycle_id=cycle.cycle_id,
             newsroom_item_count=sum(len(v) for v in newsroom_items.values()))

    # -- Dev mode: return sample newsletter --
    if settings.dev_mode or not settings.is_llm_available:
        from src.sample_data import get_sample_newsletter
        draft = get_sample_newsletter(cycle.cycle_id, state.signals)
        draft.validation_flags = _validate_newsletter(draft.content_body, draft.word_count)
        log.info("stage4c_complete_dev_mode", word_count=draft.word_count)
        return {"newsletter_draft": draft, "errors": errors}

    # -- Production mode --
    if not newsroom_items:
        errors.append("No newsroom blog items available — newsletter needs newsroom blog to run first")
        log.error("newsletter_no_newsroom_items")
        return {"newsletter_draft": None, "errors": errors}

    prompt_template = Path("prompts/newsletter.md").read_text()

    from src.llm import complete

    # Build context from newsroom blog items (the newsletter's source material)
    newsroom_context = {}
    for region in ["UK", "USA", "Australia", "Canada", "Europe", "Global"]:
        items = newsroom_items.get(region, [])
        newsroom_context[region] = [
            {
                "item_text": item.get("item_text", ""),
                "source_url": item.get("source_url", ""),
            }
            for item in items
        ]

    generation_prompt = f"""{prompt_template}

## IMPORTANT: Sourcing Rules
This is a BIMONTHLY newsletter. You are curating from the Amber Beat newsroom blog —
NOT generating new content. Select the best, most impactful items from the newsroom
blog items below and format them into the newsletter structure.

## Newsroom Blog Items by Region (SELECT FROM THESE)

**UK ({len(newsroom_context.get('UK', []))} items):**
{json.dumps(newsroom_context.get("UK", []), indent=2)}

**USA ({len(newsroom_context.get('USA', []))} items):**
{json.dumps(newsroom_context.get("USA", []), indent=2)}

**Australia ({len(newsroom_context.get('Australia', []))} items):**
{json.dumps(newsroom_context.get("Australia", []), indent=2)}

**Canada ({len(newsroom_context.get('Canada', []))} items):**
{json.dumps(newsroom_context.get("Canada", []), indent=2)}

**Europe ({len(newsroom_context.get('Europe', []))} items):**
{json.dumps(newsroom_context.get("Europe", []), indent=2)}

**Global ({len(newsroom_context.get('Global', []))} items):**
{json.dumps(newsroom_context.get("Global", []), indent=2)}

## Instructions
1. Select the 2-3 most cross-cutting items for Editor's Choice (must span 2+ regions)
2. Select the 2 best items per region for Top Global News (8 items total)
3. Use the newsroom item text as the basis — you may expand slightly for newsletter format
4. Add (Read More) links using the source URLs provided
5. Generate BOTH newsletter variants (Market Watch + amber Beat)

Separate the two variants clearly with --- MARKET WATCH --- and --- AMBER BEAT --- headers."""

    try:
        content_body = await complete(
            role="generation",
            messages=[{"role": "user", "content": generation_prompt}],
            max_tokens=4000,
        )
        word_count = len(content_body.split())
        flags = _validate_newsletter(content_body, word_count)

        draft = ContentDraft(
            cycle_id=cycle.cycle_id,
            topic_id="newsletter",
            channel=DraftChannel.NEWSLETTER,
            audience=None,
            voice=DraftVoice.NEWSLETTER_GLOBAL,
            content_body=content_body,
            word_count=word_count,
            generation_prompt=generation_prompt,
            generation_model=settings.generation_model,
            status=DraftStatus.DRAFT,
            validation_flags=flags,
        )

        log.info("stage4c_complete", word_count=word_count)
        return {"newsletter_draft": draft, "errors": errors}

    except Exception as e:
        errors.append(f"Newsletter generation failed: {e}")
        log.error("newsletter_gen_failed", error=str(e))
        return {"newsletter_draft": None, "errors": errors}


def _validate_newsletter(content: str, word_count: int) -> list[str]:
    """Validate newsletter against spec requirements."""
    flags = []

    for region in ["UK", "US", "Australia", "Canada", "Europe"]:
        if region.lower() not in content.lower():
            flags.append(f"missing_{region}_section")

    # Check both variants are present
    content_lower = content.lower()
    if "market watch" not in content_lower:
        flags.append("missing_market_watch_variant")
    if "amber beat" not in content_lower:
        flags.append("missing_amber_beat_variant")

    # Check for Editor's Choice section
    if "editor" not in content_lower:
        flags.append("missing_editors_choice_section")

    # Check for Read More links
    if content_lower.count("read more") < 8:
        flags.append(f"insufficient_read_more_links ({content_lower.count('read more')}/8 minimum)")

    return flags
