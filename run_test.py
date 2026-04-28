#!/usr/bin/env python3
"""CLI test runner -- run and test each pipeline node individually.

Usage:
    python run_test.py                    # Run all stages end-to-end
    python run_test.py stage1             # Run only Stage 1 (ingest)
    python run_test.py stage2             # Run Stage 1 + 2 (ingest + topic selection)
    python run_test.py stage3             # Run Stage 1-3 (through shortlisting)
    python run_test.py stage4             # Run Stage 1-4 (through content generation)
    python run_test.py stage5             # Run Stage 1-5 (through review doc assembly)
    python run_test.py linkedin           # Run just LinkedIn generation with sample data
    python run_test.py blog               # Run just Blog generation with sample data
    python run_test.py newsletter         # Run just Newsletter generation with sample data
    python run_test.py validate           # Run validation checks on sample content

This always uses dev_mode (sample data), so no API keys are needed.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone

# Ensure dev mode
import os
os.environ["DEV_MODE"] = "true"

from src.models.schemas import Cycle
from src.models.database import init_db
from src.graph.state import PipelineState
from src.sample_data import (
    get_sample_signals,
    get_sample_topics,
    get_sample_shortlisted_topics,
)


def _make_cycle() -> Cycle:
    return Cycle(
        cycle_id=f"TEST-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}",
        started_at=datetime.now(timezone.utc),
    )


def _print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def _print_signals(signals):
    # Group by region for readability
    by_region: dict[str, list] = {}
    for sig in signals:
        r = sig.region.value if hasattr(sig.region, "value") else str(sig.region)
        by_region.setdefault(r, []).append(sig)

    _print_header(f"STAGE 1 OUTPUT: {len(signals)} Signals")
    for region in ["UK", "USA", "Australia", "Canada", "Europe", "Global"]:
        sigs = by_region.get(region, [])
        if not sigs:
            continue
        print(f"  ── {region} ({len(sigs)} signals) ──")
        for sig in sigs:
            neg = " [NEGATIVE]" if sig.is_negative_news else ""
            comp = " [COMPETITOR]" if sig.mentions_competitor else ""
            sens = " [SENSITIVE]" if sig.is_politically_sensitive else ""
            opin = " [OPINION]" if getattr(sig, "is_opinion", False) else ""
            print(f"    [{sig.signal_id}] {sig.topic_category}")
            print(f"      {sig.headline}{neg}{comp}{sens}{opin}")
            print(f"      Source: {sig.source_name}")
            print(f"      {sig.summary[:200]}...")
            print()
    print()


def _print_topics(topics, label="TOPICS"):
    _print_header(f"{label}: {len(topics)} Topics")
    for t in topics:
        print(f"  #{t.rank}: {t.title}")
        print(f"    Urgency: {t.urgency} | Region: {t.primary_region} | Score: {t.total_score}")
        print(f"    Stakeholders: {', '.join(t.stakeholder_tags)}")
        print(f"    Signals: {t.source_signal_ids}")
        print(f"    {t.summary[:150]}...")
        if t.content_guidance:
            print(f"    Guidance: {t.content_guidance[:120]}...")
        print()


def _print_drafts(drafts, channel_name):
    _print_header(f"{channel_name}: {len(drafts)} Drafts")
    for d in drafts:
        flags = f" FLAGS: {', '.join(d.validation_flags)}" if d.validation_flags else ""
        print(f"  [{d.draft_id}] {d.voice} | {d.word_count} words | {d.status}{flags}")
        # Show first 200 chars of content
        preview = d.content_body[:200].replace('\n', ' ')
        print(f"    Preview: {preview}...")
        print()


async def run_stage1():
    """Test Stage 1: Signal ingestion."""
    from src.graph.nodes.ingest import ingest_signals

    cycle = _make_cycle()
    state = PipelineState(cycle=cycle)
    result = await ingest_signals(state)

    signals = result["signals"]
    _print_signals(signals)
    print(f"  Errors: {result.get('errors', [])}")
    return result


async def run_stage2(prev_result=None):
    """Test Stage 2: Topic selection."""
    from src.graph.nodes.topic_selection import select_topics

    if prev_result is None:
        prev_result = await run_stage1()

    cycle = prev_result.get("cycle", _make_cycle())
    state = PipelineState(cycle=cycle, signals=prev_result["signals"])
    result = await select_topics(state)

    _print_topics(result["ranked_topics"], "STAGE 2 OUTPUT: RANKED LONGLIST")
    return {**prev_result, **result}


async def run_stage3(prev_result=None):
    """Test Stage 3: Shortlisting."""
    from src.graph.nodes.shortlisting import shortlist_topics

    if prev_result is None:
        prev_result = await run_stage2()

    cycle = prev_result.get("cycle", _make_cycle())
    state = PipelineState(
        cycle=cycle,
        signals=prev_result.get("signals", []),
        ranked_topics=prev_result["ranked_topics"],
    )
    result = await shortlist_topics(state)

    _print_topics(result["shortlisted_topics"], "STAGE 3 OUTPUT: SHORTLISTED TOP 5")
    return {**prev_result, **result}


async def run_stage4(prev_result=None):
    """Test Stage 4: Content generation (all 3 agents)."""
    from src.graph.nodes.content_linkedin import generate_linkedin
    from src.graph.nodes.content_blog import generate_blogs
    from src.graph.nodes.content_newsletter import generate_newsletter

    if prev_result is None:
        prev_result = await run_stage3()

    cycle = prev_result.get("cycle", _make_cycle())
    state = PipelineState(
        cycle=cycle,
        signals=prev_result.get("signals", []),
        ranked_topics=prev_result.get("ranked_topics", []),
        shortlisted_topics=prev_result["shortlisted_topics"],
    )

    # Run all 3 agents
    li_result = await generate_linkedin(state)
    blog_result = await generate_blogs(state)
    nl_result = await generate_newsletter(state)

    _print_drafts(li_result["linkedin_drafts"], "STAGE 4A: LINKEDIN POSTS")
    _print_drafts(blog_result["blog_drafts"], "STAGE 4B: BLOG POSTS")

    nl_draft = nl_result.get("newsletter_draft")
    if nl_draft:
        _print_drafts([nl_draft], "STAGE 4C: NEWSLETTER")
    else:
        print("\n  Newsletter: FAILED (no draft generated)")

    all_drafts = li_result["linkedin_drafts"] + blog_result["blog_drafts"]
    if nl_draft:
        all_drafts.append(nl_draft)
    print(f"\n  Total drafts generated: {len(all_drafts)}")

    return {
        **prev_result,
        "linkedin_drafts": li_result["linkedin_drafts"],
        "blog_drafts": blog_result["blog_drafts"],
        "newsletter_draft": nl_draft,
    }


async def run_stage5(prev_result=None):
    """Test Stage 5: Review document assembly."""
    from src.graph.nodes.review_assembly import assemble_review_doc

    if prev_result is None:
        prev_result = await run_stage4()

    cycle = prev_result.get("cycle", _make_cycle())
    state = PipelineState(
        cycle=cycle,
        signals=prev_result.get("signals", []),
        shortlisted_topics=prev_result.get("shortlisted_topics", []),
        linkedin_drafts=prev_result.get("linkedin_drafts", []),
        blog_drafts=prev_result.get("blog_drafts", []),
        newsletter_draft=prev_result.get("newsletter_draft"),
    )
    result = await assemble_review_doc(state)

    _print_header("STAGE 5 OUTPUT: REVIEW DOCUMENT")
    print(f"  Review doc URL: {result.get('review_doc_url', 'N/A')}")

    # Print first 80 lines of the doc content (it's assembled in the node)
    total = len(prev_result.get("linkedin_drafts", [])) + len(prev_result.get("blog_drafts", []))
    if prev_result.get("newsletter_draft"):
        total += 1
    print(f"  Total drafts in review: {total}")

    return {**prev_result, **result}


async def run_linkedin_only():
    """Test just LinkedIn generation with sample data."""
    from src.graph.nodes.content_linkedin import generate_linkedin

    cycle = _make_cycle()
    signals = get_sample_signals(cycle.cycle_id)
    topics = get_sample_shortlisted_topics(cycle.cycle_id, signals)

    state = PipelineState(cycle=cycle, signals=signals, shortlisted_topics=topics)
    result = await generate_linkedin(state)

    _print_drafts(result["linkedin_drafts"], "LINKEDIN POSTS")

    # Show one full post
    if result["linkedin_drafts"]:
        d = result["linkedin_drafts"][0]
        _print_header(f"FULL POST SAMPLE: {d.voice}")
        print(d.content_body)
        print(f"\n  Word count: {d.word_count}")
        print(f"  Flags: {d.validation_flags}")


async def run_blog_only():
    """Test just Blog generation with sample data."""
    from src.graph.nodes.content_blog import generate_blogs

    cycle = _make_cycle()
    signals = get_sample_signals(cycle.cycle_id)
    topics = get_sample_shortlisted_topics(cycle.cycle_id, signals)

    state = PipelineState(cycle=cycle, signals=signals, shortlisted_topics=topics)
    result = await generate_blogs(state)

    _print_drafts(result["blog_drafts"], "BLOG POSTS")

    # Show one full blog
    if result["blog_drafts"]:
        d = result["blog_drafts"][0]
        _print_header(f"FULL BLOG SAMPLE: {d.voice}")
        print(d.content_body)
        print(f"\n  Word count: {d.word_count}")
        print(f"  Flags: {d.validation_flags}")


async def run_newsletter_only():
    """Test just Newsletter generation with sample data."""
    from src.graph.nodes.content_newsletter import generate_newsletter

    cycle = _make_cycle()
    signals = get_sample_signals(cycle.cycle_id)
    topics = get_sample_shortlisted_topics(cycle.cycle_id, signals)

    state = PipelineState(cycle=cycle, signals=signals, shortlisted_topics=topics)
    result = await generate_newsletter(state)

    nl = result.get("newsletter_draft")
    if nl:
        _print_header("NEWSLETTER")
        print(nl.content_body)
        print(f"\n  Word count: {nl.word_count}")
        print(f"  Flags: {nl.validation_flags}")
    else:
        print("  Newsletter generation failed.")


async def run_validate():
    """Run validation checks on all sample content."""
    from src.graph.nodes.content_linkedin import _validate_linkedin_post
    from src.graph.nodes.content_blog import _validate_blog
    from src.graph.nodes.content_newsletter import _validate_newsletter
    from src.models.enums import DraftVoice
    from src.sample_data import (
        get_sample_linkedin_draft,
        get_sample_blog_draft,
        get_sample_newsletter,
    )

    _print_header("VALIDATION REPORT")

    cycle = _make_cycle()
    signals = get_sample_signals(cycle.cycle_id)
    topics = get_sample_shortlisted_topics(cycle.cycle_id, signals)

    # Validate LinkedIn posts
    print("LinkedIn Posts:")
    total_flags = 0
    for topic in topics:
        for voice in [DraftVoice.AMBER_BRAND, DraftVoice.MADHUR, DraftVoice.JOOLS]:
            draft = get_sample_linkedin_draft(topic, voice, cycle.cycle_id)
            flags = _validate_linkedin_post(draft.content_body, voice, draft.word_count)
            status = "PASS" if not flags else f"FLAGGED: {', '.join(flags)}"
            print(f"  {topic.title[:30]:30s} | {voice.value:12s} | {draft.word_count:3d}w | {status}")
            total_flags += len(flags)

    # Validate blogs
    print("\nBlog Posts:")
    for topic in topics[:3]:
        for aud in ["Supply", "University", "HEA"]:
            from src.models.enums import StakeholderAudience
            audience = StakeholderAudience(aud)
            voice = DraftVoice(f"Blog{aud}")
            draft = get_sample_blog_draft(topic, audience, voice, cycle.cycle_id)
            flags = _validate_blog(draft.content_body, draft.word_count)
            status = "PASS" if not flags else f"FLAGGED: {', '.join(flags)}"
            print(f"  {topic.title[:30]:30s} | {aud:12s} | {draft.word_count:3d}w | {status}")
            total_flags += len(flags)

    # Validate newsletter
    print("\nNewsletter:")
    nl = get_sample_newsletter(cycle.cycle_id, signals)
    flags = _validate_newsletter(nl.content_body, nl.word_count)
    status = "PASS" if not flags else f"FLAGGED: {', '.join(flags)}"
    print(f"  Newsletter | {nl.word_count:3d}w | {status}")
    total_flags += len(flags)

    print(f"\n  Total validation flags: {total_flags}")
    if total_flags == 0:
        print("  All content passes validation!")


async def run_all():
    """Run the full pipeline end-to-end."""
    _print_header("AMBER CONTENT ENGINE -- FULL PIPELINE TEST (DEV MODE)")

    result = await run_stage1()
    result = await run_stage2(result)
    result = await run_stage3(result)
    result = await run_stage4(result)
    result = await run_stage5(result)

    _print_header("PIPELINE COMPLETE")
    cycle = result.get("cycle")
    if cycle:
        print(f"  Cycle: {cycle.cycle_id}")
        print(f"  Signals: {cycle.signal_count}")
        print(f"  Topics: {cycle.topic_count}")

    li = result.get("linkedin_drafts", [])
    blogs = result.get("blog_drafts", [])
    nl = result.get("newsletter_draft")
    total = len(li) + len(blogs) + (1 if nl else 0)
    print(f"  Drafts: {total} ({len(li)} LinkedIn + {len(blogs)} Blog + {'1' if nl else '0'} Newsletter)")

    # Count flags
    all_drafts = li + blogs + ([nl] if nl else [])
    flagged = [d for d in all_drafts if d.validation_flags]
    print(f"  Flagged drafts: {len(flagged)}/{total}")

    return result


def main():
    # Initialize the database
    init_db()

    command = sys.argv[1] if len(sys.argv) > 1 else "all"

    commands = {
        "all": run_all,
        "stage1": run_stage1,
        "stage2": run_stage2,
        "stage3": run_stage3,
        "stage4": run_stage4,
        "stage5": run_stage5,
        "linkedin": run_linkedin_only,
        "blog": run_blog_only,
        "newsletter": run_newsletter_only,
        "validate": run_validate,
    }

    if command not in commands:
        print(f"Unknown command: {command}")
        print(f"Available: {', '.join(commands.keys())}")
        sys.exit(1)

    asyncio.run(commands[command]())


if __name__ == "__main__":
    main()
