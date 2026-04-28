# Insights, Issues & Learnings

*Living document — update as development progresses*

---

## Architecture Insights

### What's Working Well
- **Dev mode with sample data** is invaluable — entire pipeline testable without API keys or external services
- **LangGraph interrupts** cleanly handle human gates — no custom polling/webhook needed
- **Config-driven editorial rules** means marketing team can tune topic selection without code changes
- **Prompt templates as separate files** keeps prompt engineering independent of pipeline code
- **Validation + auto-revision** catches most quality issues before human review

### Design Trade-offs Made
- **19 Claude calls per cycle in Stage 4** — could batch but chose individual calls for better per-draft quality and isolated error handling
- **Text-based review doc** instead of rich UI — simpler to build, but Google Docs integration needed for real usability
- **Single PipelineState object** — simple but large. Could fragment if pipeline grows significantly
- **Sequential publishing** (LinkedIn → Blog → Newsletter) — could parallelize but sequential is safer for error recovery

---

## Open Questions

1. **Source fetching strategy**: Should we use Firecrawl for all web scraping, or mix feedparser (RSS) + Firecrawl (HTML) + direct API calls?
2. **Google Docs vs custom UI**: Is Google Docs sufficient for review, or do we need a purpose-built review interface?
3. **Publishing tool choice**: Buffer vs LinkedIn native API? HubSpot vs Mailchimp for newsletters?
4. **Performance feedback weighting**: How much should past topic performance influence future scoring? Currently "soft signal" — need to define the weight.
5. **Admin dashboard**: Build custom (React/Next.js) or use an existing tool (Retool, Streamlit)?

---

## Known Technical Issues

| # | Issue | File | Severity | Notes |
|---|-------|------|----------|-------|
| 1 | `_fetch_source()` returns empty list | ingest.py:161 | High | Production blocker |
| 2 | Google Docs URL is placeholder | review_assembly.py:111 | High | Reviewers can't see drafts |
| 3 | All Slack notifications stubbed | Multiple files | High | No human notification |
| 4 | No rate limiting on Claude API calls | Stage 4 nodes | Medium | 19 rapid calls could throttle |
| 5 | Topic matching by title string | shortlisting.py:105 | Low | Could fail on rewritten titles |
| 6 | Revision failure silent | revision.py:72 | Low | Draft keeps original, no flag |
| 7 | No source config validation | ingest.py | Low | Malformed JSON = silent fail |
| 8 | Escalation contact TODO | editorial-guardrails.json:28 | Low | No escalation path set |

---

## Performance Considerations

- **Cycle duration estimate**: ~5-10 min for Stages 1-5 (mostly LLM latency)
- **Cost per cycle**: ~19 Sonnet calls + 2 Opus calls ≈ $2-5 per cycle depending on token usage
- **Database size**: ~50-100 rows per cycle across all tables. SQLite fine for months of dev use.
- **Bottleneck**: Stage 4 content generation (19 sequential LLM calls). Could parallelize LinkedIn posts within topics.

---

## Lessons Learned

*(Add entries as development continues)*

- TBD
