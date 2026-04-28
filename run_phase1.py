"""Phase 1 end-to-end runner.

Runs Stages 1-3 of the Amber Content Engine against real sources and writes
all output to the master Google Sheet.

    Stage 1 — scrape news from ICEF Monitor + The PIE News RSS feeds
              + Google News targeted queries (last 14 days)
    Stage 2 — LLM scores and ranks the signals into 30-50 candidate topics
    Stage 3 — LLM selects 7-12 topics per region for Amber Beat newsroom blog

Usage:
    python3 run_phase1.py                 # full run
    python3 run_phase1.py --limit 30      # cap signals at 30 for a fast test
    python3 run_phase1.py --sources-only  # fetch only; skip LLM stages
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime

# Force real mode before any src imports (settings reads this)
import os
os.environ.setdefault("DEV_MODE", "false")

from src.models.schemas import Cycle  # noqa: E402
from src.models.enums import CycleStatus  # noqa: E402
from src.settings import settings  # noqa: E402


# ── Minimal state object the three nodes expect ──────────────────────────
@dataclass
class SimpleState:
    cycle: Cycle
    signals: list = field(default_factory=list)
    ranked_topics: list = field(default_factory=list)
    shortlisted_topics: list = field(default_factory=list)
    errors: list = field(default_factory=list)


# ── Pretty-printing helpers ──────────────────────────────────────────────
BLUE = "\033[34m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def hr() -> None:
    print(DIM + "─" * 72 + RESET)


def stage(n: int, title: str) -> None:
    print(f"\n{BOLD}{BLUE}▶ Stage {n} — {title}{RESET}")
    hr()


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}!{RESET} {msg}")


def err(msg: str) -> None:
    print(f"  {RED}✗{RESET} {msg}")


# ── Main ──────────────────────────────────────────────────────────────────
async def run(limit: int | None = None, sources_only: bool = False) -> int:
    print(f"\n{BOLD}Amber Content Engine — Phase 1 Runner{RESET}")
    print(
        f"{DIM}Provider: {settings.llm_provider} | "
        f"Generation: {settings.generation_model} | "
        f"Editorial: {settings.editorial_model} | "
        f"Dev mode: {settings.dev_mode}{RESET}"
    )

    if not settings.is_llm_available:
        err("No LLM API key configured — aborting")
        return 1

    # 1. Build cycle
    now = datetime.utcnow()
    cycle_id = f"cycle-{now.strftime('%Y%m%d-%H%M%S')}"
    cycle_date = now.strftime("%-d %b %Y")
    cycle = Cycle(cycle_id=cycle_id, stage=1, status=CycleStatus.RUNNING)
    state = SimpleState(cycle=cycle)
    print(f"\n{DIM}Cycle: {cycle_id}  ({cycle_date}){RESET}")

    # 2. Sheets client
    try:
        from src.integrations.sheets import SheetsClient
        sheets = SheetsClient()
        ok("Connected to Google Sheet")
    except Exception as e:
        err(f"Cannot connect to Sheet: {e}")
        return 1

    # 3. Archive previous cycle data before starting fresh
    stage(0, "Archiving previous cycle data")
    try:
        counts = sheets.archive_and_clear(cycle_id=cycle_id, cycle_date=cycle_date)
        archived_total = sum(v for v in counts.values() if v > 0)
        if archived_total > 0:
            ok(f"Archived {archived_total} rows from previous cycle")
            for tab, count in counts.items():
                if count > 0:
                    print(f"    {tab}: {count} rows → Archive")
                elif count == 0:
                    print(f"    {tab}: (was empty)")
        else:
            ok("No previous data to archive — fresh start")
    except Exception as e:
        warn(f"Archive failed (non-fatal): {e}")

    sheets.update_dashboard(
        cycle_id=cycle_id,
        stage="1: Ingest",
        status="Running",
        started_at=cycle.started_at.isoformat(timespec="seconds"),
    )

    # ── Stage 1 ──
    stage(1, "Fetching signals from RSS + Google News")
    try:
        from src.graph.nodes.ingest import ingest_signals
        result = await ingest_signals(state)
    except Exception as e:
        err(f"Stage 1 crashed: {e}")
        traceback.print_exc()
        sheets.append_errors(cycle_id, "Stage 1", [str(e)])
        return 1

    signals = result.get("signals", []) or []       # kept only
    all_signals = result.get("all_signals", signals)  # all (for sheet)

    if limit and len(signals) > limit:
        signals = signals[:limit]
        warn(f"Capped signals at --limit {limit}")

    state.signals = signals
    if result.get("cycle"):
        state.cycle = result["cycle"]
    state.cycle.signal_count = len(signals)

    for e_msg in result.get("errors", []):
        warn(e_msg)

    dropped = len(all_signals) - len(signals)
    ok(f"{len(signals)} signals kept, {dropped} dropped (PR/opinion/irrelevant)")

    if all_signals:
        try:
            sheets.append_signals(all_signals, cycle_date=cycle_date)
            ok(f"All {len(all_signals)} signals written to sheet (status column shows kept/dropped)")
        except Exception as e:
            err(f"Sheet write failed: {e}")

    if not signals:
        warn("All signals were filtered out — nothing to rank")
        sheets.update_dashboard(status="Failed: all filtered", last_error="No relevant signals")
        return 1

    if sources_only:
        print(f"\n{DIM}--sources-only flag set, stopping after Stage 1{RESET}")
        sheets.update_dashboard(
            signals=len(signals),
            status="Stage 1 complete (sources-only)",
        )
        return 0

    sheets.update_dashboard(
        stage="2: Topic Selection",
        status="Running",
        signals=len(signals),
    )

    # ── Stage 2 ──
    stage(2, "Ranking topics with LLM")
    try:
        from src.graph.nodes.topic_selection import select_topics
        result = await select_topics(state)
    except Exception as e:
        err(f"Stage 2 crashed: {e}")
        traceback.print_exc()
        sheets.append_errors(cycle_id, "Stage 2", [str(e)])
        return 1

    ranked = result.get("ranked_topics", []) or []
    state.ranked_topics = ranked
    if result.get("cycle"):
        state.cycle = result["cycle"]
    state.cycle.topic_count = len(ranked)

    for e_msg in result.get("errors", []):
        warn(e_msg)

    ok(f"{len(ranked)} topics ranked")

    if ranked:
        try:
            sheets.append_ranked_topics(ranked, cycle_date=cycle_date)
            ok("Ranked topics written to sheet")
        except Exception as e:
            err(f"Sheet write failed: {e}")
    else:
        warn("No topics ranked — cannot shortlist")
        sheets.update_dashboard(status="Failed: no topics")
        return 1

    sheets.update_dashboard(
        stage="3: Shortlisting",
        status="Running",
        ranked=len(ranked),
    )

    # ── Stage 3 ──
    stage(3, "Shortlisting 7-12 per region for Amber Beat newsroom blog")
    try:
        from src.graph.nodes.shortlisting import shortlist_topics
        result = await shortlist_topics(state)
    except Exception as e:
        err(f"Stage 3 crashed: {e}")
        traceback.print_exc()
        sheets.append_errors(cycle_id, "Stage 3", [str(e)])
        return 1

    shortlisted = result.get("shortlisted_topics", []) or []
    state.shortlisted_topics = shortlisted
    if result.get("cycle"):
        state.cycle = result["cycle"]
    state.cycle.topic_count = len(shortlisted)

    for e_msg in result.get("errors", []):
        warn(e_msg)

    ok(f"{len(shortlisted)} topics shortlisted")

    if shortlisted:
        try:
            sheets.append_shortlist(shortlisted, cycle_date=cycle_date)
            ok("Shortlist written to sheet (Gate 1 ready for review)")
        except Exception as e:
            err(f"Sheet write failed: {e}")

    # ── Finalise ──
    state.cycle.status = CycleStatus.AWAITING_TOPIC_APPROVAL
    state.cycle.stage = 3

    try:
        sheets.append_cycle(
            state.cycle,
            counts={
                "signals": len(signals),
                "ranked": len(ranked),
                "shortlisted": len(shortlisted),
            },
        )
    except Exception as e:
        warn(f"Cycle row not written: {e}")

    sheets.update_dashboard(
        cycle_id=cycle_id,
        stage="Gate 1 — awaiting human review",
        status="Gate 1 Waiting",
        signals=len(signals),
        ranked=len(ranked),
        shortlisted=len(shortlisted),
    )

    # ── Summary ──
    print(f"\n{BOLD}{GREEN}✅ Phase 1 complete{RESET}")
    hr()

    # Group shortlisted by region
    by_region: dict[str, list] = {}
    for t in shortlisted:
        r = t.primary_region.value if hasattr(t.primary_region, "value") else t.primary_region
        by_region.setdefault(r, []).append(t)

    print(f"{BOLD}Shortlisted topics for Amber Beat newsroom blog ({len(shortlisted)} total){RESET}\n")
    for region_name in ["UK", "USA", "Australia", "Canada", "Europe", "Global"]:
        topics_in_region = by_region.get(region_name, [])
        if not topics_in_region:
            continue
        print(f"  {BOLD}{BLUE}── {region_name} ({len(topics_in_region)} topics) ──{RESET}")
        for t in topics_in_region[:8]:  # show up to 8 per region
            stakeholders = ", ".join(
                a.value if hasattr(a, "value") else a for a in (t.stakeholder_tags or [])
            )
            urgency = t.urgency.value if hasattr(t.urgency, "value") else t.urgency
            print(f"    {t.rank}. {t.title}")
            print(f"       {DIM}{urgency}  |  {stakeholders}{RESET}")
        if len(topics_in_region) > 8:
            print(f"       {DIM}... and {len(topics_in_region) - 8} more{RESET}")
        print()

    print(f"{DIM}Full results & Gate 1 review:{RESET}")
    print(
        f"  https://docs.google.com/spreadsheets/d/{settings.google_master_sheet_id}\n"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 1 of the content engine")
    parser.add_argument("--limit", type=int, default=None, help="Cap signals (for fast test)")
    parser.add_argument("--sources-only", action="store_true", help="Stop after Stage 1")
    args = parser.parse_args()
    return asyncio.run(run(limit=args.limit, sources_only=args.sources_only))


if __name__ == "__main__":
    sys.exit(main())
