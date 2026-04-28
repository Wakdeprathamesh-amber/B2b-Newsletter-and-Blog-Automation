"""UI API routes — powers the web control panel.

Clean architecture:
  Phase 1: Scrape signals → Rank topics (7-12/region) → Write to sheet
  Human Review: In Ranked Topics tab — approve, tag channels, pick voice/lens
  Phase 2: Generate content per channel from approved+tagged topics

No shortlist step. Human IS the shortlister via channel tags.
"""

import asyncio
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.models.schemas import Cycle, Topic
from src.models.enums import CycleStatus, Region, UrgencyLevel, StakeholderAudience
from src.settings import settings
from src.integrations.slack import get_slack_client

router = APIRouter(prefix="/api/ui")

# ── Slack client ──────────────────────────────────────────────────────────
slack = get_slack_client()

# ── In-memory state ───────────────────────────────────────────────────────

_state: dict = {
    "cycle_id": None, "status": "idle", "step": None,
    "signals": 0, "ranked": 0, "newsroom_items": 0,
    "linkedin_drafts": 0, "blog_drafts": 0, "newsletter": 0,
    "running_task": None, "last_error": None, "last_success": None,
    "sheet_url": f"https://docs.google.com/spreadsheets/d/{settings.google_master_sheet_id}",
}
_cancel_requested = False


# ── Models ────────────────────────────────────────────────────────────────

class StatusResponse(BaseModel):
    cycle_id: str | None
    status: str
    step: str | None
    signals: int
    ranked: int
    newsroom_items: int
    linkedin_drafts: int
    blog_drafts: int
    newsletter: int
    running_task: str | None
    last_error: str | None
    last_success: str | None
    sheet_url: str


class ApprovalStatus(BaseModel):
    total: int
    approved: int
    pending: int
    rejected: int
    newsroom_tagged: int
    linkedin_tagged: int
    blog_tagged: int
    newsletter_tagged: int


# ── Helpers ───────────────────────────────────────────────────────────────

def _sheets():
    from src.integrations.sheets import SheetsClient
    return SheetsClient()


def _set_running(task: str):
    global _cancel_requested
    _cancel_requested = False
    _state.update(running_task=task, status="running", last_error=None, step=None)


def _done(msg: str):
    _state.update(running_task=None, status="idle", last_success=msg, step=None)


def _fail(msg: str):
    _state.update(running_task=None, status="failed", last_error=msg, step=None)


def _check_cancel():
    if _cancel_requested:
        raise RuntimeError("Cancelled by user")


RMAP = {"uk": Region.UK, "usa": Region.USA, "us": Region.USA,
        "australia": Region.AUSTRALIA, "canada": Region.CANADA,
        "europe": Region.EUROPE, "global": Region.GLOBAL}
AMAP = {"supply": StakeholderAudience.SUPPLY,
        "university": StakeholderAudience.UNIVERSITY,
        "hea": StakeholderAudience.HEA}


def _read_approved_topics(sheets, channel_filter: str | None = None) -> list[Topic]:
    """Read approved topics from Ranked Topics tab, optionally filtered by channel."""
    ws = sheets._ws("Ranked Topics")
    data = ws.get_all_values()
    if len(data) < 2:
        return []

    headers = data[0]
    col = {h: i for i, h in enumerate(headers)}
    topics = []

    for row in data[1:]:
        def g(name):
            idx = col.get(name)
            if idx is None or idx >= len(row): return ""
            return row[idx].strip()

        # Must be approved
        decision = g("decision").lower()
        if decision not in ("approve", "approved", "edit"):
            continue

        # Channel filter
        if channel_filter:
            channels = g("channels").lower()
            if channel_filter.lower() not in channels:
                continue

        region = RMAP.get(g("primary_region").lower(), Region.GLOBAL)
        tags = [AMAP[t.strip().lower()] for t in g("stakeholder_tags").split(",")
                if t.strip().lower() in AMAP]
        try:
            rank = int(g("rank"))
        except ValueError:
            rank = 99

        topics.append(Topic(
            topic_id=g("topic_id") or f"t-{len(topics)+1}",
            title=g("edited_title") or g("title"),
            summary=g("edited_summary") or g("summary"),
            content_guidance=g("content_guidance") or g("reviewer_notes"),
            rank=min(rank, 60),
            urgency=UrgencyLevel.TIME_SENSITIVE,
            primary_region=region,
            stakeholder_tags=tags,
            source_urls=[u.strip() for u in g("source_references").split("\n") if u.strip()],
        ))

        # Attach voice/lens as extra attributes for downstream use
        topics[-1]._linkedin_voice = g("linkedin_voice")
        topics[-1]._blog_lens = g("blog_lens")

    return topics


# ── Status ────────────────────────────────────────────────────────────────

@router.get("/status")
async def get_status() -> StatusResponse:
    if _state["status"] == "idle" and _state["signals"] == 0 and not _state["running_task"]:
        try:
            _hydrate_from_dashboard()
        except Exception:
            pass
    return StatusResponse(**_state)


def _hydrate_from_dashboard():
    sheets = _sheets()
    ws = sheets._ws("Dashboard")
    data = ws.get_all_values()
    metrics = {}
    for row in data[1:]:
        if len(row) >= 2 and row[0] and row[1]:
            metrics[row[0]] = row[1]
    if metrics.get("Active Cycle ID"):
        _state["cycle_id"] = metrics["Active Cycle ID"]
        for key, metric in [("signals", "Signals Captured"), ("ranked", "Topics Ranked"),
                            ("linkedin_drafts", "LinkedIn Drafts"), ("newsletter", "Newsletter Drafts")]:
            try:
                _state[key] = int(metrics.get(metric, 0))
            except (ValueError, TypeError):
                pass


# ── Approvals ─────────────────────────────────────────────────────────────

@router.get("/approvals")
async def get_approvals() -> ApprovalStatus:
    try:
        sheets = _sheets()
        ws = sheets._ws("Ranked Topics")
        data = ws.get_all_values()
        if len(data) < 2:
            return ApprovalStatus(total=0, approved=0, pending=0, rejected=0,
                                  newsroom_tagged=0, linkedin_tagged=0, blog_tagged=0, newsletter_tagged=0)

        headers = data[0]
        col = {h: i for i, h in enumerate(headers)}
        rows = data[1:]
        total = len(rows)

        def g(row, name):
            idx = col.get(name)
            if idx is None or idx >= len(row): return ""
            return row[idx].strip().lower()

        approved = sum(1 for r in rows if g(r, "decision") in ("approve", "approved", "edit"))
        rejected = sum(1 for r in rows if g(r, "decision") in ("reject", "rejected"))
        pending = total - approved - rejected

        newsroom = sum(1 for r in rows if "newsroom" in g(r, "channels"))
        linkedin = sum(1 for r in rows if "linkedin" in g(r, "channels"))
        blog = sum(1 for r in rows if "blog" in g(r, "channels"))
        newsletter = sum(1 for r in rows if "newsletter" in g(r, "channels"))

        return ApprovalStatus(
            total=total, approved=approved, pending=pending, rejected=rejected,
            newsroom_tagged=newsroom, linkedin_tagged=linkedin,
            blog_tagged=blog, newsletter_tagged=newsletter,
        )
    except Exception:
        return ApprovalStatus(total=0, approved=0, pending=0, rejected=0,
                              newsroom_tagged=0, linkedin_tagged=0, blog_tagged=0, newsletter_tagged=0)


# ── Stop ──────────────────────────────────────────────────────────────────

@router.post("/stop")
async def stop_task():
    global _cancel_requested
    if not _state["running_task"]:
        return {"message": "Nothing running"}
    _cancel_requested = True
    _state["step"] = "Cancelling..."
    return {"message": f"Cancel requested for: {_state['running_task']}"}


# ── Phase 1: Start New Cycle (scrape + rank, NO shortlisting) ────────────

@router.post("/phase1/start")
async def start_phase1():
    if _state["running_task"]:
        raise HTTPException(400, f"Already running: {_state['running_task']}")
    _set_running("Phase 1: Scrape + Rank")
    asyncio.create_task(_run_phase1())
    return {"message": "Phase 1 started"}


async def _run_phase1():
    try:
        now = datetime.now(timezone.utc)
        cycle_id = f"cycle-{now.strftime('%Y%m%d-%H%M%S')}"
        cycle_date = now.strftime("%-d %b %Y")
        _state["cycle_id"] = cycle_id

        sheets = _sheets()

        # Notify Slack: cycle started
        slack.send_message_async(f"🚀 New cycle started: `{cycle_id}`")

        # Archive previous cycle
        _state["step"] = "Archiving previous cycle..."
        sheets.archive_and_clear(cycle_id=cycle_id, cycle_date=cycle_date)
        _check_cancel()

        # Stage 1: Ingest
        _state["step"] = "Scraping signals from RSS + Google News..."
        slack.send_message_async(f"⏳ Stage 1: Scraping signals... (`{cycle_id}`)")
        cycle = Cycle(cycle_id=cycle_id, stage=1, status=CycleStatus.RUNNING)

        @dataclass
        class SimpleState:
            cycle: Cycle
            signals: list = field(default_factory=list)
            ranked_topics: list = field(default_factory=list)
            errors: list = field(default_factory=list)

        state = SimpleState(cycle=cycle)

        from src.graph.nodes.ingest import ingest_signals
        r1 = await ingest_signals(state)
        signals = r1.get("signals", [])         # kept only (for ranking)
        all_signals = r1.get("all_signals", signals)  # all (for sheet)
        _state["signals"] = len(signals)
        _check_cancel()

        if not all_signals:
            slack.notify_cycle_failed(cycle_id, "No signals captured")
            _fail("No signals captured")
            return

        # Write ALL signals to sheet (including dropped) — status column shows why
        sheets.append_signals(all_signals, cycle_date=cycle_date)

        if not signals:
            error_msg = f"All {len(all_signals)} signals were filtered out (PR/opinion/irrelevant). Check the Signals tab."
            slack.notify_cycle_failed(cycle_id, error_msg)
            _fail(error_msg)
            return

        # Stage 2: Rank (parallel per-region)
        _state["step"] = f"Ranking {len(signals)} signals (7-12 per region, parallel)..."
        slack.send_message_async(f"⏳ Stage 2: Ranking {len(signals)} signals... (`{cycle_id}`)")
        state.signals = signals
        if r1.get("cycle"):
            state.cycle = r1["cycle"]

        from src.graph.nodes.topic_selection import select_topics
        r2 = await select_topics(state)
        ranked = r2.get("ranked_topics", [])
        _state["ranked"] = len(ranked)
        _check_cancel()

        sheets.append_ranked_topics(ranked, cycle_date=cycle_date)

        # Update dashboard + cycles
        sheets.update_dashboard(
            cycle_id=cycle_id, stage="Review topics in sheet",
            status="Review", signals=len(signals), ranked=len(ranked),
        )
        try:
            sheets.append_cycle(
                Cycle(cycle_id=cycle_id, stage=2, status=CycleStatus.AWAITING_TOPIC_APPROVAL),
                counts={"signals": len(signals), "ranked": len(ranked)},
            )
        except Exception:
            pass

        # Notify Slack: cycle complete, awaiting review
        slack.notify_cycle_completed(
            cycle_id,
            counts={"signals": len(signals), "ranked": len(ranked)},
            duration_min=int((datetime.now(timezone.utc) - now).total_seconds() / 60),
        )
        slack.notify_gate1_waiting(cycle_id, len(ranked))

        _done(f"Phase 1 complete: {len(signals)} signals, {len(ranked)} ranked topics. Review and tag in sheet.")

    except RuntimeError as e:
        if "Cancelled" in str(e):
            slack.send_message_async(f"⏸️ Cycle cancelled by user: `{_state.get('cycle_id', 'unknown')}`")
            _done("Cancelled by user")
        else:
            slack.notify_error(_state.get("cycle_id", "unknown"), "Phase 1", str(e))
            _fail(str(e))
            traceback.print_exc()
    except Exception as e:
        slack.notify_error(_state.get("cycle_id", "unknown"), "Phase 1", str(e))
        _fail(str(e))
        traceback.print_exc()


# ── Generate: Newsroom Blog ──────────────────────────────────────────────

@router.post("/generate/newsroom")
async def gen_newsroom():
    if _state["running_task"]:
        raise HTTPException(400, f"Already running: {_state['running_task']}")
    _set_running("Generating Newsroom Blog")
    asyncio.create_task(_run_newsroom())
    return {"message": "Newsroom generation started"}


async def _run_newsroom():
    try:
        sheets = _sheets()
        cycle_id = _state.get("cycle_id") or "manual"
        
        _state["step"] = "Reading topics tagged 'Newsroom'..."
        topics = _read_approved_topics(sheets, channel_filter="Newsroom")

        if not topics:
            error_msg = "No topics tagged for Newsroom. In the sheet, set decision to 'Approve' and add 'Newsroom' to the channels column."
            slack.notify_error(cycle_id, "Newsroom Generation", error_msg)
            _fail(error_msg)
            return

        _state["step"] = f"Generating newsroom items from {len(topics)} topics..."
        slack.send_message_async(f"⏳ Generating Newsroom Blog from {len(topics)} topics... (`{cycle_id}`)")
        
        from run_phase2 import generate_newsroom_items

        items, errors = await generate_newsroom_items(topics, cycle_id)
        total = sum(len(v) for v in items.values())
        _state["newsroom_items"] = total

        _state["step"] = "Writing to sheet..."
        cycle_date = datetime.now(timezone.utc).strftime("%-d %b %Y")
        topic_titles = {t.topic_id: t.title for t in topics}
        sheets.append_newsroom_items(items, cycle_id=cycle_id,
                                     cycle_date=cycle_date, topic_titles=topic_titles)

        slack.notify_content_generated(cycle_id, "newsroom", total)
        _done(f"Newsroom Blog: {total} items written to sheet")
    except Exception as e:
        slack.notify_error(_state.get("cycle_id", "unknown"), "Newsroom Generation", str(e))
        _fail(str(e))
        traceback.print_exc()


# ── Generate: LinkedIn ────────────────────────────────────────────────────

@router.post("/generate/linkedin")
async def gen_linkedin():
    if _state["running_task"]:
        raise HTTPException(400, f"Already running: {_state['running_task']}")
    _set_running("Generating LinkedIn Posts")
    asyncio.create_task(_run_linkedin())
    return {"message": "LinkedIn generation started"}


async def _run_linkedin():
    try:
        sheets = _sheets()
        cycle_id = _state.get("cycle_id") or "manual"
        
        _state["step"] = "Reading topics tagged 'LinkedIn'..."
        topics = _read_approved_topics(sheets, channel_filter="LinkedIn")

        if not topics:
            error_msg = "No topics tagged for LinkedIn. In the sheet, add 'LinkedIn' to the channels column."
            slack.notify_error(cycle_id, "LinkedIn Generation", error_msg)
            _fail(error_msg)
            return

        _state["step"] = f"Generating LinkedIn posts from {len(topics)} topics..."
        slack.send_message_async(f"⏳ Generating LinkedIn posts from {len(topics)} topics... (`{cycle_id}`)")
        
        from run_phase2 import generate_linkedin_posts

        drafts, errors = await generate_linkedin_posts(topics, cycle_id)
        _state["linkedin_drafts"] = len(drafts)

        _state["step"] = "Writing to sheet..."
        topic_titles = {t.topic_id: t.title for t in topics}
        sheets.append_linkedin_drafts(drafts, topic_titles=topic_titles)

        slack.notify_content_generated(cycle_id, "linkedin", len(drafts))
        _done(f"LinkedIn: {len(drafts)} posts written to sheet")
    except Exception as e:
        slack.notify_error(_state.get("cycle_id", "unknown"), "LinkedIn Generation", str(e))
        _fail(str(e))
        traceback.print_exc()


# ── Generate: Blogs ───────────────────────────────────────────────────────

@router.post("/generate/blogs")
async def gen_blogs():
    if _state["running_task"]:
        raise HTTPException(400, f"Already running: {_state['running_task']}")
    _set_running("Generating Blog Posts")
    asyncio.create_task(_run_blogs())
    return {"message": "Blog generation started"}


async def _run_blogs():
    try:
        sheets = _sheets()
        cycle_id = _state.get("cycle_id") or "manual"
        
        _state["step"] = "Reading topics tagged 'Blog'..."
        topics = _read_approved_topics(sheets, channel_filter="Blog")

        if not topics:
            error_msg = "No topics tagged for Blog. In the sheet, add 'Blog' to the channels column."
            slack.notify_error(cycle_id, "Blog Generation", error_msg)
            _fail(error_msg)
            return

        _state["step"] = f"Generating blogs from {len(topics)} topics..."
        slack.send_message_async(f"⏳ Generating Blog posts from {len(topics)} topics... (`{cycle_id}`)")

        from src.graph.state import PipelineState
        cycle = Cycle(cycle_id=cycle_id, stage=4)
        pipe_state = PipelineState(cycle=cycle, shortlisted_topics=topics)

        from src.graph.nodes.content_blog import generate_blogs as gen
        result = await gen(pipe_state)
        drafts = result.get("blog_drafts", [])
        _state["blog_drafts"] = len(drafts)

        slack.notify_content_generated(cycle_id, "blog", len(drafts))
        _done(f"Blogs: {len(drafts)} posts generated")
    except Exception as e:
        slack.notify_error(_state.get("cycle_id", "unknown"), "Blog Generation", str(e))
        _fail(str(e))
        traceback.print_exc()


# ── Generate: Newsletter ──────────────────────────────────────────────────

@router.post("/generate/newsletter")
async def gen_newsletter():
    if _state["running_task"]:
        raise HTTPException(400, f"Already running: {_state['running_task']}")
    _set_running("Generating Newsletter")
    asyncio.create_task(_run_newsletter())
    return {"message": "Newsletter generation started"}


async def _run_newsletter():
    try:
        sheets = _sheets()
        cycle_id = _state.get("cycle_id") or "manual"
        
        _state["step"] = "Reading newsroom blog items..."

        ws = sheets._ws("Newsroom Blog")
        data = ws.get_all_values()
        if len(data) < 2:
            error_msg = "No newsroom blog items found. Generate the Newsroom Blog first."
            slack.notify_error(cycle_id, "Newsletter Generation", error_msg)
            _fail(error_msg)
            return

        headers = data[0]
        col = {h: i for i, h in enumerate(headers)}
        newsroom_items: dict[str, list] = {}
        for row in data[1:]:
            region = row[col.get("region", 0)] if col.get("region") is not None else "Global"
            newsroom_items.setdefault(region, []).append({
                "item_text": row[col.get("item_text", 0)] if col.get("item_text") is not None else "",
                "source_url": row[col.get("source_url", 0)] if col.get("source_url") is not None else "",
            })

        total = sum(len(v) for v in newsroom_items.values())
        _state["step"] = f"Generating newsletter from {total} newsroom items..."
        slack.send_message_async(f"⏳ Generating Newsletter from {total} newsroom items... (`{cycle_id}`)")

        topics = _read_approved_topics(sheets)

        from run_phase2 import generate_newsletter_from_newsroom
        draft, errors = await generate_newsletter_from_newsroom(newsroom_items, topics, cycle_id)

        if draft:
            sheets.append_newsletter(draft)
            _state["newsletter"] = 1
            slack.notify_content_generated(cycle_id, "newsletter", 1)
            _done(f"Newsletter: {draft.word_count} words written to sheet")
        else:
            error_msg = "Newsletter generation returned no content"
            slack.notify_error(cycle_id, "Newsletter Generation", error_msg)
            _fail(error_msg)
    except Exception as e:
        slack.notify_error(_state.get("cycle_id", "unknown"), "Newsletter Generation", str(e))
        _fail(str(e))
        traceback.print_exc()
