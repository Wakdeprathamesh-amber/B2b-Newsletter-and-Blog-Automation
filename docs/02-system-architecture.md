# System Architecture

## Pipeline Overview

The system runs in recurring bi-monthly cycles. Built on **LangGraph** with **async Python**, **FastAPI** for the API layer, and **Claude** (Sonnet for generation, Opus for editorial) as the LLM backbone.

```
Stage 1: Ingest Signals (22 sources, 4 regions)
    |
Stage 2: Topic Selection (score & rank 10-15 candidates)
    |
Stage 3: Shortlisting (top 5 topics, stakeholder/region matrix)
    |
[HUMAN GATE 1] — Topic Approval (Slack notify, interrupt, 24h deadline)
    |
Stage 4A: LinkedIn (15 posts)  ---|
Stage 4B: Blog (3 posts)       ---|--> parallel
Stage 4C: Newsletter (1 draft) ---|
    |
Stage 5: Review Doc Assembly (compile all 19 drafts)
    |
[HUMAN GATE 2] — Content Review (approve/edit/block per draft)
    |--- Revision loop (max 2 rounds) ---> back to Gate 2
    |
Stage 6A: LinkedIn Publish (Buffer/LinkedIn API, staggered schedule)
Stage 6B: Blog Publish (Notion/CMS)
Stage 6C: Newsletter Publish (HubSpot/Mailchimp)
    |
Stage 7: Feedback Loop (7 days post-publish, engagement metrics)
    |
END — Cycle Complete
```

## Core Data Entities

| Entity | Purpose | Key Fields |
|--------|---------|------------|
| **Signal** | Raw data from sources | source_url, region, topic_category, flags |
| **Topic** | Ranked editorial topic from signals | rank, urgency, stakeholder_tags, scores |
| **ContentDraft** | Generated content piece | channel, voice, content_body, validation_flags |
| **Cycle** | One pipeline run | stage (1-7), status, counts |
| **ReviewSession** | Logged human review event | gate, decisions[], reviewer_name |
| **LogEntry** | Audit trail | event_type, entity_id, actor, details |

## Tech Stack

- **Pipeline**: LangGraph (state graph with interrupts)
- **LLM**: Claude Sonnet (generation), Claude Opus (editorial scoring)
- **API**: FastAPI + Uvicorn
- **Database**: SQLite (dev) / PostgreSQL (prod) via SQLAlchemy
- **Prompts**: Markdown templates in `prompts/`
- **Config**: JSON files in `config/` (sources, rules, guardrails, stakeholders)
- **Scheduler**: APScheduler (cron-based, default: every 2 weeks Thu 7am London)

## State Management

Single `PipelineState` object flows through the entire graph. Uses LangGraph reducers:
- `_merge_lists` — appends new items (signals, errors)
- `_replace` — takes newer value (topics, drafts, scalars)

Human gates use LangGraph's `interrupt()` to pause the graph. External input resumes via FastAPI endpoints.

## Configuration Store

All editorial rules, voice profiles, sources, and publishing settings are stored in config files — editable without code changes:
- `config/sources.json` — 22 monitored sources with priority/region/type
- `config/topic-rules.json` — always-cover, never-cover, seasonal triggers
- `config/editorial-guardrails.json` — negative news protocol, sensitive topics
- `config/stakeholders.json` — 3 audiences, 3 voice personas
