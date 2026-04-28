"""Phase 2 runner — Content Generation.

Reads the Shortlist tab from the master Google Sheet (7-12 topics per region),
then generates:
  - LinkedIn posts (top topics x 3 voices: Amber Brand, Madhur, Jools)
  - 1 bimonthly newsletter (Market Watch + amber Beat variants, sourced from
    the newsroom blog shortlisted topics)

Results are written back to the LinkedIn Drafts and Newsletter tabs.

Usage:
    python3 run_phase2.py                  # full run (all 5 topics)
    python3 run_phase2.py --topics 2       # only first N shortlisted topics
    python3 run_phase2.py --linkedin-only  # skip newsletter
    python3 run_phase2.py --newsletter-only  # skip LinkedIn
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime

import os
os.environ.setdefault("DEV_MODE", "false")

from src.models.schemas import Cycle, Topic, ContentDraft  # noqa: E402
from src.models.enums import (  # noqa: E402
    CycleStatus, DraftChannel, DraftStatus, DraftVoice,
    Region, StakeholderAudience, UrgencyLevel,
)
from src.settings import settings  # noqa: E402


# ── Pretty-printing helpers ──────────────────────────────────────────────
BLUE = "\033[34m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def hr() -> None:
    print(DIM + "-" * 72 + RESET)


def stage(n: str, title: str) -> None:
    print(f"\n{BOLD}{BLUE}> {n} -- {title}{RESET}")
    hr()


def ok(msg: str) -> None:
    print(f"  {GREEN}+{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}!{RESET} {msg}")


def err(msg: str) -> None:
    print(f"  {RED}x{RESET} {msg}")


# ── Read shortlist from Google Sheet ─────────────────────────────────────
REGION_MAP = {
    "uk": Region.UK,
    "usa": Region.USA,
    "us": Region.USA,
    "australia": Region.AUSTRALIA,
    "europe": Region.EUROPE,
    "global": Region.GLOBAL,
}

AUDIENCE_MAP = {
    "supply": StakeholderAudience.SUPPLY,
    "university": StakeholderAudience.UNIVERSITY,
    "hea": StakeholderAudience.HEA,
}


def parse_shortlist_rows(headers: list[str], rows: list[list[str]]) -> list[Topic]:
    """Convert raw sheet rows into Topic objects."""
    topics: list[Topic] = []
    col = {h: i for i, h in enumerate(headers)}

    for row in rows:
        def g(name: str) -> str:
            idx = col.get(name)
            if idx is None or idx >= len(row):
                return ""
            return row[idx].strip()

        # Parse region
        region_str = g("primary_region").lower()
        region = REGION_MAP.get(region_str, Region.GLOBAL)

        # Parse stakeholder tags
        raw_tags = [t.strip() for t in g("stakeholder_tags").split(",") if t.strip()]
        tags = []
        for t in raw_tags:
            mapped = AUDIENCE_MAP.get(t.lower())
            if mapped:
                tags.append(mapped)

        # Parse rank
        try:
            rank = int(g("rank"))
        except ValueError:
            rank = 99

        topic = Topic(
            topic_id=g("topic_id") or f"topic-{uuid.uuid4().hex[:8]}",
            title=g("title"),
            summary=g("summary"),
            content_guidance=g("content_guidance"),
            rank=min(rank, 60),
            urgency=UrgencyLevel.TIME_SENSITIVE,
            primary_region=region,
            stakeholder_tags=tags,
            source_urls=[u.strip() for u in g("source_references").split("\n") if u.strip()],
            edited_title=g("edited_title") or None,
            edited_summary=g("edited_summary") or None,
        )
        topics.append(topic)

    return topics


# ── Main ─────────────────────────────────────────────────────────────────
async def run(
    topic_limit: int | None = None,
    linkedin_only: bool = False,
    newsletter_only: bool = False,
) -> int:
    print(f"\n{BOLD}Amber Content Engine -- Phase 2 Runner{RESET}")
    print(
        f"{DIM}Provider: {settings.llm_provider} | "
        f"Model: {settings.generation_model} | "
        f"Dev mode: {settings.dev_mode}{RESET}"
    )

    if not settings.is_llm_available:
        err("No LLM API key configured -- aborting")
        return 1

    # 1. Connect to sheet and read shortlist
    stage("1", "Reading shortlist from Google Sheet")
    try:
        from src.integrations.sheets import SheetsClient
        sheets = SheetsClient()
        ok("Connected to Google Sheet")
    except Exception as e:
        err(f"Cannot connect to Sheet: {e}")
        return 1

    try:
        ws = sheets._ws("Shortlist")
        all_data = ws.get_all_values()
    except Exception as e:
        err(f"Cannot read Shortlist tab: {e}")
        return 1

    if len(all_data) < 2:
        err("Shortlist tab is empty (no data rows)")
        return 1

    headers = all_data[0]
    data_rows = all_data[1:]
    topics = parse_shortlist_rows(headers, data_rows)

    if topic_limit and len(topics) > topic_limit:
        topics = topics[:topic_limit]
        warn(f"Limited to first {topic_limit} topics")

    ok(f"{len(topics)} shortlisted topics loaded:")
    for t in topics:
        print(f"    {t.rank}. {t.title} [{t.primary_region}]")

    # 2. Build cycle
    now = datetime.utcnow()
    cycle_id = f"cycle-{now.strftime('%Y%m%d-%H%M%S')}"
    cycle = Cycle(cycle_id=cycle_id, stage=4, status=CycleStatus.RUNNING)

    # Also read signals for newsletter context (from Signals tab)
    signals_for_newsletter = []
    try:
        sig_ws = sheets._ws("Signals")
        sig_data = sig_ws.get_all_values()
        if len(sig_data) > 1:
            sig_headers = sig_data[0]
            signals_for_newsletter = sig_data[1:]
            ok(f"{len(signals_for_newsletter)} signals available for newsletter context")
    except Exception:
        warn("Could not read Signals tab -- newsletter will use topic data only")

    sheets.update_dashboard(
        cycle_id=cycle_id,
        stage="4: Content Generation",
        status="Running",
    )

    linkedin_drafts: list[ContentDraft] = []
    newsroom_items: dict[str, list] = {}
    newsletter_draft: ContentDraft | None = None
    all_errors: list[str] = []
    topic_titles = {t.topic_id: t.title for t in topics}

    # ── Stage 4A: LinkedIn (top 5 topics x 3 voices) ──
    if not newsletter_only:
        stage("4A", "Generating LinkedIn posts (top 5 topics)")
        try:
            # LinkedIn uses top 5 topics only
            li_topics = sorted(topics, key=lambda t: t.rank)[:5]
            linkedin_drafts, li_errors = await generate_linkedin_posts(
                li_topics, cycle_id
            )
            all_errors.extend(li_errors)
            ok(f"{len(linkedin_drafts)} LinkedIn drafts generated")

            # Show summary
            by_voice: dict[str, int] = {}
            flagged = 0
            for d in linkedin_drafts:
                v = d.voice.value if hasattr(d.voice, "value") else str(d.voice)
                by_voice[v] = by_voice.get(v, 0) + 1
                if d.validation_flags:
                    flagged += 1
            for v, c in by_voice.items():
                print(f"    {v}: {c} posts")
            if flagged:
                warn(f"{flagged} posts have validation flags")

            # Write to sheet
            sheets.append_linkedin_drafts(linkedin_drafts, topic_titles=topic_titles)
            ok("LinkedIn drafts written to sheet")

        except Exception as e:
            err(f"Stage 4A crashed: {e}")
            traceback.print_exc()
            all_errors.append(f"Stage 4A: {e}")

    # ── Stage 4D: Amber Beat Newsroom Blog (weekly, 7-12 items per region) ──
    # Newsroom blog uses ALL topics from the sheet (ranked = 7-12 per region)
    # not just the shortlisted 5 per region
    stage("4D", "Generating Amber Beat newsroom blog items (from all ranked topics)")
    try:
        newsroom_items, nr_errors = await generate_newsroom_items(
            topics, cycle_id
        )
        all_errors.extend(nr_errors)

        total_items = sum(len(v) for v in newsroom_items.values())
        ok(f"{total_items} newsroom blog items generated")
        for region in ["UK", "USA", "Australia", "Europe", "Global"]:
            items = newsroom_items.get(region, [])
            if items:
                print(f"    {region}: {len(items)} items")

        # Write to sheet
        cycle_date = datetime.utcnow().strftime("%-d %b %Y")
        sheets.append_newsroom_items(
            newsroom_items, cycle_id=cycle_id,
            cycle_date=cycle_date, topic_titles=topic_titles,
        )
        ok("Newsroom blog items written to sheet")

    except Exception as e:
        err(f"Stage 4D crashed: {e}")
        traceback.print_exc()
        all_errors.append(f"Stage 4D: {e}")

    # ── Stage 4C: Newsletter (bimonthly — curated from newsroom items) ──
    if not linkedin_only:
        stage("4C", "Generating newsletter (bimonthly, from newsroom blog)")
        try:
            newsletter_draft, nl_errors = await generate_newsletter_from_newsroom(
                newsroom_items, topics, cycle_id
            )
            all_errors.extend(nl_errors)

            if newsletter_draft:
                ok(f"Newsletter generated ({newsletter_draft.word_count} words)")
                if newsletter_draft.validation_flags:
                    for f in newsletter_draft.validation_flags:
                        warn(f"Validation: {f}")

                sheets.append_newsletter(newsletter_draft)
                ok("Newsletter written to sheet")
            else:
                err("Newsletter generation returned no content")

        except Exception as e:
            err(f"Stage 4C crashed: {e}")
            traceback.print_exc()
            all_errors.append(f"Stage 4C: {e}")

    # ── Finalise ──
    if all_errors:
        sheets.append_errors(cycle_id, "Phase 2", all_errors)

    li_count = len(linkedin_drafts)
    nr_count = sum(len(v) for v in newsroom_items.values())
    nl_count = 1 if newsletter_draft else 0

    sheets.update_dashboard(
        stage="Gate 2 -- awaiting content review",
        status="Gate 2 Waiting",
        linkedin=li_count,
        newsletter=nl_count,
    )

    print(f"\n{BOLD}{GREEN}Phase 2 complete{RESET}")
    hr()
    print(f"  Newsroom items:  {nr_count}")
    print(f"  LinkedIn drafts: {li_count}")
    print(f"  Newsletter:      {nl_count}")
    if all_errors:
        print(f"  Errors:          {len(all_errors)}")
    print(f"\n{DIM}Review content in the sheet:{RESET}")
    print(f"  https://docs.google.com/spreadsheets/d/{settings.google_master_sheet_id}\n")
    return 0


# ── LinkedIn generation ──────────────────────────────────────────────────
async def generate_linkedin_posts(
    topics: list[Topic], cycle_id: str
) -> tuple[list[ContentDraft], list[str]]:
    """Generate 5 topics x 3 voices = 15 LinkedIn posts."""

    from src.graph.nodes.content_linkedin import VOICE_CONFIGS, _validate_linkedin_post
    from src.llm import complete
    from pathlib import Path

    prompt_template = Path("prompts/linkedin-post.md").read_text()
    voices = [DraftVoice.AMBER_BRAND, DraftVoice.MADHUR, DraftVoice.JOOLS]
    drafts: list[ContentDraft] = []
    errors: list[str] = []

    for topic in topics:
        for voice in voices:
            voice_config = VOICE_CONFIGS[voice]
            import json

            generation_prompt = f"""{prompt_template}

## This Specific Post

Topic: {topic.edited_title or topic.title}
Summary: {topic.edited_summary or topic.summary}
Content guidance: {topic.content_guidance}
Region: {topic.primary_region}
Stakeholder audience: {', '.join(str(a) for a in topic.stakeholder_tags)}
Source URLs: {', '.join(topic.source_urls[:3])}

## Voice for This Post
Voice: {voice_config['label']}
Tone: {voice_config['tone']}
Format: {voice_config['format']}
Length: {voice_config['length']}
Include hashtags: {voice_config['hashtags']}
Rules: {json.dumps(voice_config['rules'])}

Write the LinkedIn post now. Return ONLY the post text (and hashtags if applicable)."""

            print(f"    Generating: {topic.title[:40]}... [{voice.value}]")

            try:
                content_body = await complete(
                    role="generation",
                    messages=[{"role": "user", "content": generation_prompt}],
                    max_tokens=2000,
                )
                word_count = len(content_body.split())
                flags = _validate_linkedin_post(content_body, voice, word_count)

                draft = ContentDraft(
                    draft_id=f"li-{uuid.uuid4().hex[:8]}",
                    cycle_id=cycle_id,
                    topic_id=topic.topic_id,
                    channel=DraftChannel.LINKEDIN,
                    audience=topic.stakeholder_tags[0] if topic.stakeholder_tags else None,
                    voice=voice,
                    content_body=content_body,
                    word_count=word_count,
                    generation_prompt=generation_prompt,
                    generation_model=settings.generation_model,
                    status=DraftStatus.DRAFT,
                    validation_flags=flags,
                )
                drafts.append(draft)

                status = "OK" if not flags else f"FLAGS: {', '.join(flags)}"
                print(f"      {word_count}w -- {status}")

            except Exception as e:
                errors.append(f"LinkedIn [{topic.title[:30]} / {voice}]: {e}")
                err(f"Failed: {topic.title[:40]} [{voice.value}] -- {e}")

    return drafts, errors


# ── Newsroom Blog generation ────────────────────────────────────────────
async def generate_newsroom_items(
    topics: list[Topic], cycle_id: str
) -> tuple[dict[str, list], list[str]]:
    """Generate Amber Beat newsroom blog items: 7-12 per region, 21-25 words each."""

    from src.graph.nodes.content_newsroom import NEWSROOM_PROMPT, REGION_ORDER, _topic_priority
    from src.llm import complete_json
    import json

    errors: list[str] = []

    # Group topics by region and sort by priority
    regional_topics: dict[str, list[dict]] = {}
    for region in REGION_ORDER:
        region_key = region.value
        region_topics = [t for t in topics if str(t.primary_region) == region_key
                         or (hasattr(t.primary_region, "value") and t.primary_region.value == region_key)]
        region_topics.sort(key=_topic_priority)
        regional_topics[region_key] = [
            {
                "topic_id": t.topic_id,
                "title": t.edited_title or t.title,
                "summary": t.edited_summary or t.summary,
                "source_urls": t.source_urls[:2] if t.source_urls else [],
            }
            for t in region_topics
        ]

    prompt = NEWSROOM_PROMPT.format(
        regional_topics=json.dumps(regional_topics, indent=2)
    )

    print("    Generating newsroom blog items per region...")
    for region, items in regional_topics.items():
        print(f"      {region}: {len(items)} topics to convert")

    try:
        raw_items = await complete_json(
            role="generation",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8000,
        )

        newsroom_items: dict[str, list[dict]] = {}
        for region in ["UK", "USA", "Australia", "Europe", "Global"]:
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
                    "valid": 18 <= word_count <= 28,
                })
            newsroom_items[region] = validated

        return newsroom_items, errors

    except Exception as e:
        errors.append(f"Newsroom blog: {e}")
        err(f"Newsroom blog generation failed: {e}")
        return {}, errors


# ── Newsletter generation (from newsroom items) ────────────────────────
async def generate_newsletter_from_newsroom(
    newsroom_items: dict[str, list],
    topics: list[Topic],
    cycle_id: str,
) -> tuple[ContentDraft | None, list[str]]:
    """Generate bimonthly newsletter by curating from newsroom blog items."""

    from src.graph.nodes.content_newsletter import _validate_newsletter
    from src.llm import complete
    from pathlib import Path
    import json

    prompt_template = Path("prompts/newsletter.md").read_text()
    errors: list[str] = []

    if not newsroom_items:
        errors.append("No newsroom items available for newsletter")
        return None, errors

    # Build context from newsroom blog items
    newsroom_context = {}
    for region in ["UK", "USA", "Australia", "Europe", "Global"]:
        items = newsroom_items.get(region, [])
        newsroom_context[region] = [
            {"item_text": item.get("item_text", ""), "source_url": item.get("source_url", "")}
            for item in items
        ]

    generation_prompt = f"""{prompt_template}

## IMPORTANT: Sourcing Rules
This is a BIMONTHLY newsletter. You are curating from the Amber Beat newsroom blog.
Select the best, most impactful items from the newsroom blog items below.

## Newsroom Blog Items by Region (SELECT FROM THESE)

**UK ({len(newsroom_context.get('UK', []))} items):**
{json.dumps(newsroom_context.get("UK", []), indent=2)}

**USA ({len(newsroom_context.get('USA', []))} items):**
{json.dumps(newsroom_context.get("USA", []), indent=2)}

**Australia ({len(newsroom_context.get('Australia', []))} items):**
{json.dumps(newsroom_context.get("Australia", []), indent=2)}

**Europe ({len(newsroom_context.get('Europe', []))} items):**
{json.dumps(newsroom_context.get("Europe", []), indent=2)}

**Global ({len(newsroom_context.get('Global', []))} items):**
{json.dumps(newsroom_context.get("Global", []), indent=2)}

Select 2-3 items for Editor's Choice (must span 2+ regions).
Select 2 best items per region for Top Global News (8 items total).
Generate BOTH newsletter variants (Market Watch + amber Beat).
Separate with --- MARKET WATCH --- and --- AMBER BEAT --- headers."""

    print("    Generating newsletter from newsroom items...")

    try:
        content_body = await complete(
            role="generation",
            messages=[{"role": "user", "content": generation_prompt}],
            max_tokens=4000,
        )
        word_count = len(content_body.split())
        flags = _validate_newsletter(content_body, word_count)

        draft = ContentDraft(
            draft_id=f"nl-{uuid.uuid4().hex[:8]}",
            cycle_id=cycle_id,
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

        return draft, errors

    except Exception as e:
        errors.append(f"Newsletter: {e}")
        err(f"Newsletter generation failed: {e}")
        return None, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 2 — Content Generation")
    parser.add_argument("--topics", type=int, default=None, help="Limit to first N topics")
    parser.add_argument("--linkedin-only", action="store_true", help="Only generate LinkedIn posts")
    parser.add_argument("--newsletter-only", action="store_true", help="Only generate newsletter")
    args = parser.parse_args()
    return asyncio.run(run(
        topic_limit=args.topics,
        linkedin_only=args.linkedin_only,
        newsletter_only=args.newsletter_only,
    ))


if __name__ == "__main__":
    sys.exit(main())
