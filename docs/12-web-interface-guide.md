# Web Interface Guide — Amber Content Engine

*Complete guide to using the web control panel*

---

## Quick Start

1. **Start the server:**
   ```bash
   python src/main.py
   ```

2. **Open the web interface:**
   ```
   http://localhost:8000
   ```

3. **Workflow:**
   - Click "Start New Cycle" → wait 5-15 min
   - Open Google Sheet → review and tag topics
   - Click content generation buttons → wait 2-5 min each
   - Review content in Google Sheet

---

## System Status: ✅ READY FOR PRODUCTION

### What's Working
- ✅ Web interface fully functional
- ✅ All latest enhancements integrated
- ✅ Automatic cycle archiving
- ✅ Real-time progress updates
- ✅ Error handling and recovery
- ✅ Google Sheets integration
- ✅ Multi-cycle support with history preservation

### What's NOT Working (Known Limitations)
- ⚠️ Google Docs review URL (placeholder only)
- ⚠️ Slack notifications (stubbed)
- ⚠️ Publishing to LinkedIn/Blog/Newsletter (Phase 3 not started)

**None of these affect the web interface or content generation!**

---

## Timing Estimates

### Phase 1: Scrape & Rank
**Total: 5-15 minutes**

| Step | Time | What Happens |
|------|------|--------------|
| Archive | 30-60 sec | Backs up previous cycle to Archive tabs |
| Scrape | 2-5 min | Fetches from RSS feeds + Google News |
| Rank | 2-5 min | LLM ranks topics (parallel per region) |
| Shortlist | 1-2 min | LLM selects 7-12 per region |

**You can close the page during this time.** Refresh to check progress.

### Phase 2: Human Review
**Manual — no time limit**

Open the Google Sheet and for each topic:
- Set `decision` to Approve or Reject
- Set `channels`: Newsroom, LinkedIn, Blog, Newsletter
- If LinkedIn → pick `linkedin_voice`
- If Blog → pick `blog_lens`

### Phase 3: Content Generation

| Button | Time | What It Generates |
|--------|------|-------------------|
| Newsroom Blog | 2-3 min | 7-12 items per region (21-25 words each) |
| LinkedIn Posts | 3-5 min | 5 topics × 3 voices = 15 posts |
| Blog Posts | 2-4 min | 3 blog posts with different lenses |
| Newsletter | 1-2 min | Bimonthly newsletter from newsroom items |

**Run Newsroom first if you want Newsletter** (newsletter curates from newsroom items).

---

## Cycle Management: How Multiple Cycles Work

### Starting a New Cycle

When you click "Start New Cycle", the system:

1. **Archives current data** (30-60 seconds):
   ```
   Active Tab              →  Archive Tab
   ─────────────────────────────────────────
   Signals                 →  Archive - Signals
   Ranked Topics           →  Archive - Ranked Topics
   Newsroom Blog           →  Archive - Newsroom Blog
   ```

2. **Clears active tabs** (keeps headers):
   - Signals
   - Ranked Topics (was "Shortlist")
   - Newsroom Blog
   - LinkedIn Drafts
   - Blog Drafts
   - Newsletter

3. **Starts fresh cycle**:
   - New cycle_id: `cycle-20260427-143022`
   - New cycle_date: `27 Apr 2026`
   - Dashboard updated with new cycle info

### What Gets Preserved

✅ **Archived (with cycle_id + cycle_date):**
- All signals (including dropped ones)
- All ranked topics (with decisions)
- All newsroom blog items

✅ **History tabs (cumulative):**
- Cycles (one row per cycle)
- Errors (all errors across cycles)
- Dashboard (shows current cycle only)

❌ **NOT archived (regenerated each cycle):**
- LinkedIn Drafts
- Blog Drafts
- Newsletter

### Archive Tab Structure

**Archive - Signals:**
```
cycle_id | cycle_date | signal_id | source | headline | region | status | ...
```

**Archive - Ranked Topics:**
```
cycle_id | cycle_date | topic_id | rank | title | region | decision | ...
```

**Archive - Newsroom Blog:**
```
cycle_id | cycle_date | region | rank | item_text | word_count | ...
```

### Finding Previous Cycle Data

1. Open Google Sheet
2. Go to Archive tabs
3. Filter by `cycle_id` or `cycle_date`

Example:
```
cycle_id: cycle-20260427-143022
cycle_date: 27 Apr 2026
```

---

## Web Interface Features

### Status Dashboard

**Cycle Info:**
- Current cycle ID
- Status badge (Idle / Running / Failed)
- Real-time progress indicator

**Metrics:**
- Signals captured
- Topics ranked
- Newsroom items generated
- LinkedIn drafts
- Newsletter drafts

### Progress Indicator

Shows current step when running:
```
⏳ Archiving previous cycle...
⏳ Scraping signals from RSS + Google News...
⏳ Ranking 45 signals (7-12 per region, parallel)...
⏳ Generating newsroom items from 38 topics...
```

### Approval Status

Shows review progress:
```
Review Status                    [Refresh]
─────────────────────────────────────────
5/38 approved  ████░░░░░░░░░░░░  13%

Newsroom: 12  LinkedIn: 8  Blog: 3  Newsletter: 0
```

### Error Handling

- Toast notifications for success/error
- Log panel shows timestamped events
- Failed cycles show last error in status
- All errors logged to Errors tab in sheet

---

## Common Workflows

### Weekly Newsroom Blog

1. **Monday morning:** Start new cycle
2. **Wait 5-15 min** for Phase 1 to complete
3. **Review topics** in Google Sheet (30-60 min)
   - Approve 7-12 topics per region
   - Tag all with "Newsroom"
4. **Click "Newsroom Blog"** button
5. **Wait 2-3 min** for generation
6. **Review items** in Newsroom Blog tab
7. **Publish** to website (manual for now)

### Bimonthly Newsletter

1. **Run Newsroom Blog first** (see above)
2. **Click "Newsletter"** button
3. **Wait 1-2 min** for generation
4. **Review** in Newsletter tab
5. **Publish** to email platform (manual for now)

### LinkedIn Posts

1. **After Phase 1:** Review and tag topics
   - Approve 5 topics
   - Tag with "LinkedIn"
   - Pick `linkedin_voice` for each (Amber Brand / Madhur / Jools)
2. **Click "LinkedIn Posts"** button
3. **Wait 3-5 min** for 15 posts (5 topics × 3 voices)
4. **Review** in LinkedIn Drafts tab
5. **Publish** to LinkedIn (manual for now)

### Blog Posts

1. **After Phase 1:** Review and tag topics
   - Approve 3 topics
   - Tag with "Blog"
   - Pick `blog_lens` for each (Supply / University / HEA)
2. **Click "Blog Posts"** button
3. **Wait 2-4 min** for 3 posts
4. **Review** in Blog Drafts tab
5. **Publish** to CMS (manual for now)

---

## Troubleshooting

### "All signals were filtered out"

**Cause:** All scraped signals were PR/opinion/irrelevant.

**Fix:**
1. Check Signals tab → `status` column shows why each was dropped
2. Adjust filters in `config/topic-rules.json` if too aggressive
3. Add more RSS sources in `config/sources.json`

### "No topics tagged for [channel]"

**Cause:** You didn't tag any topics for that channel in the sheet.

**Fix:**
1. Open Google Sheet → Ranked Topics tab
2. Set `decision` to "Approve"
3. Add channel name to `channels` column (e.g., "Newsroom, LinkedIn")
4. Click the generation button again

### "Newsletter generation returned no content"

**Cause:** No newsroom blog items available.

**Fix:**
1. Run "Newsroom Blog" button first
2. Wait for completion
3. Then run "Newsletter" button

### Progress stuck / no updates

**Cause:** Backend crashed or connection lost.

**Fix:**
1. Check terminal for errors
2. Restart server: `python src/main.py`
3. Refresh web page
4. Check Errors tab in Google Sheet

### Rate limit errors

**Cause:** Too many LLM API calls too fast.

**Fix:**
1. Wait 1-2 minutes
2. Click "Stop" button
3. Restart the failed stage
4. Consider adding rate limiting (see `docs/08-insights-and-issues.md`)

---

## API Endpoints (for developers)

### Status
```
GET /api/ui/status
→ Returns current cycle status, metrics, running task
```

### Approvals
```
GET /api/ui/approvals
→ Returns approval counts and channel tags
```

### Phase 1
```
POST /api/ui/phase1/start
→ Starts new cycle (archive + scrape + rank)
```

### Content Generation
```
POST /api/ui/generate/newsroom
POST /api/ui/generate/linkedin
POST /api/ui/generate/blogs
POST /api/ui/generate/newsletter
→ Generates content for specified channel
```

### Stop
```
POST /api/ui/stop
→ Cancels running task
```

---

## Configuration Files

### Sources
`config/sources.json` — RSS feeds and Google News queries

### Topic Rules
`config/topic-rules.json` — Filtering and scoring rules

### Stakeholders
`config/stakeholders.json` — Audience definitions

### Editorial Guardrails
`config/editorial-guardrails.json` — Content validation rules

### Voice Profiles
`config/voices/` — LinkedIn voice and blog lens definitions

---

## Next Steps (Phase 3 — Not Yet Built)

- [ ] LinkedIn publishing (Buffer/LinkedIn API)
- [ ] Blog CMS publishing (Notion)
- [ ] Newsletter publishing (HubSpot/Mailchimp)
- [ ] Performance feedback loop
- [ ] Publishing schedule view
- [ ] Cycle performance reports

---

## Support

**Documentation:**
- `docs/09-full-specification.md` — Complete system spec
- `docs/11-amber-beat-sop.md` — Newsroom blog SOP
- `docs/08-insights-and-issues.md` — Known issues

**Logs:**
- Terminal output (real-time)
- Google Sheet → Errors tab (persistent)
- Google Sheet → Cycles tab (history)

**Contact:**
- Check `docs/08-insights-and-issues.md` for known issues
- Review terminal logs for error details
- Check Google Sheet Errors tab for LLM failures
