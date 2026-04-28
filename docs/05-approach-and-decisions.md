# Approach & Key Decisions

## Design Principles

1. **Human-in-the-loop, not human-in-the-way** — Two review gates give editorial control without blocking automation. Everything between gates runs autonomously.

2. **Config-driven, not code-driven** — Editorial rules, voice profiles, sources, and guardrails live in JSON/markdown config files. Marketing team can update without engineering changes.

3. **Traceable by default** — Every signal → topic → draft → published piece is linked. Every human decision logged. Every AI prompt stored with its output.

4. **Dev mode first** — Entire pipeline runs offline with sample data. Enables rapid iteration without API keys or external services.

5. **Fail gracefully** — Individual source failures don't block the cycle. Individual draft failures don't block the review. Always continue and flag.

## Architecture Decisions

### Why LangGraph?
- Native support for graph-based workflows with conditional branching
- Built-in `interrupt()` for human gates — clean pause/resume without custom state machines
- State checkpointing to PostgreSQL in production (resume from last stage on crash)
- Parallel node execution for Stage 4 (LinkedIn + Blog + Newsletter)

### Why Claude (Sonnet + Opus)?
- Sonnet for content generation (15+ calls per cycle) — fast, cost-effective
- Opus for editorial scoring (topic selection, shortlisting) — deeper reasoning for ranking decisions
- Both via Anthropic API directly (no LangChain wrapper overhead)

### Why FastAPI for the API Layer?
- Async-native (matches async pipeline)
- Simple REST endpoints for cycle trigger, gate approval, status checks
- Future: serves the admin dashboard frontend

### Why SQLite for Dev / PostgreSQL for Prod?
- SQLite is zero-config, ships with Python — perfect for local dev
- PostgreSQL for production concurrency, durability, and LangGraph checkpoint storage
- SQLAlchemy ORM abstracts the difference

### Why Separate Prompt Files?
- Prompts in `prompts/*.md` instead of inline strings
- Enables versioning, A/B testing, and non-engineer editing
- Each prompt is a complete system instruction for one pipeline stage

## Content Strategy Decisions

### Voice Architecture
- **3 LinkedIn voices**: Amber Brand (corporate/data-led), Madhur (supply/thought leadership), Jools (university/partnerships)
- **3 Blog lenses**: Supply Partners (yield/occupancy), Universities (recruitment/policy), HEA/Agents (corridors/destinations)
- **1 Newsletter**: Regional sections (UK, USA, Australia, Europe) — covers all audiences

### Validation Rules
- LinkedIn: word count 150-300, no "I" in brand voice, no hashtags on personal voices
- Blog: 600-900 words, must have headings, must cite data
- Newsletter: under 500 words, all 4 regional sections present, each has a data point

### Auto-Revision
- If validation fails, AI gets one automatic revision attempt before flagging for human review
- Gate 2 allows up to 2 human-directed revision rounds per draft
- After 2 rounds, draft is blocked — human must handle manually
