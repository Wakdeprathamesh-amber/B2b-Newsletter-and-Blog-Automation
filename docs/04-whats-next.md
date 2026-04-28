# What's Next — Remaining Work

*Last updated: 2026-04-03*

## Priority 1: Production Blockers (Must-Have)

### 1. Source Fetching (`src/graph/nodes/ingest.py:161-169`)
The `_fetch_source()` function is stubbed — returns empty list in production mode. Need to implement:
- **RSS feeds** via `feedparser` (ICEF Monitor, PIE News, Property Week, PBSA News)
- **Web scraping** via Firecrawl API (HESA, Home Office, DHA, UCAS, etc.)
- **Direct API calls** for official data sources where available
- Per-source fetch strategies based on `sources.json` config

### 2. Slack Notifications (Multiple files)
All Slack sends are commented out / TODOs:
- `human_gate_1.py:60-65` — Topic approval brief notification
- `human_gate_2.py:34` — Content review notification
- `review_assembly.py:118-126` — Review doc ready notification
- `publish.py:66, 96, 125` — Publishing schedule notifications
- `feedback.py:89` — Performance report notification

### 3. Google Docs Integration (`review_assembly.py:111-116`)
Currently generates placeholder URL. Need:
- `google-api-python-client` integration
- Create formatted Google Doc from review text
- Return shareable URL

---

## Priority 2: Publishing Pipeline (Phase 3)

### 4. LinkedIn Publishing (`publish.py:52-62`)
- Buffer API or LinkedIn Marketing API integration
- Staggered posting schedule (already calculated in code)
- Schedule preview → human confirmation → auto-publish

### 5. Blog CMS Publishing (`publish.py:80-89`)
- Notion API integration (or alternative CMS)
- Push formatted blog as draft page
- Notify blog publisher to add image + schedule

### 6. Newsletter Publishing (`publish.py:114-118`)
- HubSpot or Mailchimp API integration
- Map sections to email template
- Push as draft for manual send confirmation

---

## Priority 3: Feedback Loop

### 7. Metrics Collection (`feedback.py:35-57`)
- LinkedIn API — impressions, clicks, reactions per post
- Buffer Analytics — engagement data
- HubSpot/Mailchimp — open rate, CTR, unsubscribes
- Calculate topic performance scores

### 8. Performance Score Persistence (`feedback.py:92`)
- Write scores back to Topic store
- Feed into next cycle's topic selection ranking

---

## Priority 4: Polish & Testing

### 9. Unit Tests (`tests/` is empty)
- Test each node's logic in isolation
- Test validation functions
- Test state transitions and graph flow
- Test persistence layer

### 10. API: Cycle History (`routes.py:200-201`)
- Query CycleRow from database
- Return past cycles with stats and links

### 11. Production Database Setup
- PostgreSQL setup + connection
- Migration tooling (Alembic)
- LangGraph PostgresSaver checkpoint config

### 12. Admin Dashboard
- Cycle overview UI
- Topic review interface
- Content review interface
- Publishing schedule view
- Configuration editor
- Logs viewer

---

## Known Issues & Edge Cases

| Issue | Location | Impact | Severity |
|-------|----------|--------|----------|
| No rate limiting on Claude calls | Stage 4 (19 calls) | Could hit API limits | Medium |
| Topic matching by title in shortlisting | `shortlisting.py:105` | Could fail if Claude rewrites titles | Low |
| Silent failure on source config errors | `ingest.py` | Empty source list, no warning | Low |
| Revision failure not flagged | `revision.py:72-75` | Draft keeps original silently | Low |
| Escalation contact is TODO | `editorial-guardrails.json:28` | No escalation path configured | Low |
