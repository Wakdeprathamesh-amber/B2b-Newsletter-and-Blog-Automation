"""FastAPI routes for the Amber Content Engine.

Endpoints for:
- Triggering new cycles
- Human gate interactions (approve/edit/reject topics and content)
- Cycle status and history
- Admin operations (config, logs)
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from langgraph.types import Command
from pydantic import BaseModel

from src.graph.pipeline import get_compiled_pipeline
from src.graph.state import PipelineState
from src.models.schemas import Cycle, ReviewDecision

router = APIRouter(prefix="/api/v1")


# ── Request models ──────────────────────────────────────────────────────────


class TriggerCycleRequest(BaseModel):
    cycle_id: str | None = None  # Auto-generate if not provided


class Gate1Response(BaseModel):
    """Human response for topic approval gate."""

    reviewer_name: str
    action: str = "approve_all"  # approve_all | approve_with_edits | pause
    decisions: list[ReviewDecision] = []


class Gate2Response(BaseModel):
    """Human response for content review gate."""

    reviewer_name: str
    decisions: list[ReviewDecision] = []


# ── Cycle management ────────────────────────────────────────────────────────


@router.post("/cycles/trigger")
async def trigger_cycle(request: TriggerCycleRequest):
    """Start a new content cycle."""
    cycle_id = request.cycle_id or f"{datetime.utcnow().strftime('%Y-W%V')}"

    cycle = Cycle(cycle_id=cycle_id)
    initial_state = PipelineState(cycle=cycle)

    pipeline = get_compiled_pipeline()
    thread_config = {"configurable": {"thread_id": cycle_id}}

    # Start the pipeline (runs until first interrupt = Gate 1)
    result = await pipeline.ainvoke(initial_state, config=thread_config)

    return {
        "cycle_id": cycle_id,
        "status": "running",
        "message": "Cycle started. Pipeline will run until topic approval gate.",
    }


@router.get("/cycles/{cycle_id}/status")
async def get_cycle_status(cycle_id: str):
    """Get the current status of a cycle."""
    pipeline = get_compiled_pipeline()
    thread_config = {"configurable": {"thread_id": cycle_id}}

    try:
        state = await pipeline.aget_state(thread_config)
        if state.values:
            cycle_data = state.values.get("cycle")
            return {
                "cycle_id": cycle_id,
                "status": cycle_data.status if cycle_data else "unknown",
                "stage": cycle_data.stage if cycle_data else 0,
                "signal_count": cycle_data.signal_count if cycle_data else 0,
                "topic_count": cycle_data.topic_count if cycle_data else 0,
                "draft_count": cycle_data.draft_count if cycle_data else 0,
                "next_action": state.next,  # Which node is pending
                "errors": state.values.get("errors", []),
            }
        return {"cycle_id": cycle_id, "status": "not_found"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Cycle not found: {e}")


# ── Human Gate 1 — Topic Approval ──────────────────────────────────────────


@router.get("/cycles/{cycle_id}/gate1")
async def get_gate1_topics(cycle_id: str):
    """Get the topics awaiting approval for Gate 1."""
    pipeline = get_compiled_pipeline()
    thread_config = {"configurable": {"thread_id": cycle_id}}

    state = await pipeline.aget_state(thread_config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Cycle not found")

    shortlisted = state.values.get("shortlisted_topics", [])
    ranked = state.values.get("ranked_topics", [])

    return {
        "cycle_id": cycle_id,
        "shortlisted_topics": [t.model_dump() for t in shortlisted],
        "longlist_topics": [t.model_dump() for t in ranked[5:]] if len(ranked) > 5 else [],
    }


@router.post("/cycles/{cycle_id}/gate1/approve")
async def approve_gate1(cycle_id: str, response: Gate1Response):
    """Submit topic approval decisions for Gate 1."""
    pipeline = get_compiled_pipeline()
    thread_config = {"configurable": {"thread_id": cycle_id}}

    # Resume the interrupted graph with the human's response
    human_input = {
        "action": response.action,
        "reviewer_name": response.reviewer_name,
        "decisions": [d.model_dump() for d in response.decisions],
    }

    # Resume the pipeline — it will continue from gate1_wait through content generation
    # until it hits Gate 2
    result = await pipeline.ainvoke(
        Command(resume=human_input),
        config=thread_config,
    )

    return {
        "cycle_id": cycle_id,
        "status": "approved",
        "message": "Topics approved. Content generation started.",
    }


# ── Human Gate 2 — Content Review ──────────────────────────────────────────


@router.get("/cycles/{cycle_id}/gate2")
async def get_gate2_content(cycle_id: str):
    """Get all drafts awaiting review for Gate 2."""
    pipeline = get_compiled_pipeline()
    thread_config = {"configurable": {"thread_id": cycle_id}}

    state = await pipeline.aget_state(thread_config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Cycle not found")

    linkedin = state.values.get("linkedin_drafts", [])
    blogs = state.values.get("blog_drafts", [])
    newsletter = state.values.get("newsletter_draft")

    return {
        "cycle_id": cycle_id,
        "review_doc_url": state.values.get("review_doc_url", ""),
        "revision_round": state.values.get("revision_round", 0),
        "linkedin_drafts": [d.model_dump() for d in linkedin],
        "blog_drafts": [d.model_dump() for d in blogs],
        "newsletter_draft": newsletter.model_dump() if newsletter else None,
    }


@router.post("/cycles/{cycle_id}/gate2/approve")
async def approve_gate2(cycle_id: str, response: Gate2Response):
    """Submit content review decisions for Gate 2."""
    pipeline = get_compiled_pipeline()
    thread_config = {"configurable": {"thread_id": cycle_id}}

    human_input = {
        "reviewer_name": response.reviewer_name,
        "decisions": [d.model_dump() for d in response.decisions],
    }

    result = await pipeline.ainvoke(
        Command(resume=human_input),
        config=thread_config,
    )

    return {
        "cycle_id": cycle_id,
        "status": "reviewed",
        "message": "Content review submitted. Pipeline will revise or publish.",
    }


# ── Cycle History ───────────────────────────────────────────────────────────


@router.get("/cycles")
async def list_cycles():
    """List all cycles (from database)."""
    # TODO: Query CycleRow from database
    return {"cycles": [], "message": "TODO: Implement cycle history query"}


# ── Admin / Config ──────────────────────────────────────────────────────────


@router.get("/config/sources")
async def get_sources():
    """Get the current source configuration."""
    import json
    with open("config/sources.json") as f:
        return json.load(f)


@router.get("/config/topic-rules")
async def get_topic_rules():
    """Get the current topic rules."""
    import json
    with open("config/topic-rules.json") as f:
        return json.load(f)


@router.get("/config/stakeholders")
async def get_stakeholders():
    """Get the current stakeholder configuration."""
    import json
    with open("config/stakeholders.json") as f:
        return json.load(f)
