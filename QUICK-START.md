# Amber Content Engine — Quick Start

## 🚀 Start the System

```bash
# 1. Test Slack integration (optional)
python test_slack.py

# 2. Start the server
python src/main.py

# 3. Open web interface
# → http://localhost:8000
```

**Slack Notifications:** If configured, you'll receive real-time updates in your Slack channel!

---

## ⏱️ Timing Guide

| Task | Time | Can Close Page? |
|------|------|-----------------|
| Phase 1: Scrape & Rank | 5-15 min | ✅ Yes |
| Human Review (in Sheet) | Manual | N/A |
| Newsroom Blog | 2-3 min | ✅ Yes |
| LinkedIn Posts | 3-5 min | ✅ Yes |
| Blog Posts | 2-4 min | ✅ Yes |
| Newsletter | 1-2 min | ✅ Yes |

**You can close the page during generation.** Refresh to check progress.

---

## 📋 Workflow

### 1️⃣ Start New Cycle
```
Click "Start New Cycle" → Wait 5-15 min
```

**What happens:**
- Archives previous cycle data
- Scrapes RSS feeds + Google News
- Ranks topics with LLM (parallel per region)
- Writes to Google Sheet

### 2️⃣ Review & Tag Topics
```
Open Google Sheet → Ranked Topics tab
```

**For each topic:**
- Set `decision` to **Approve** or **Reject**
- Set `channels`: **Newsroom**, **LinkedIn**, **Blog**, **Newsletter**
- If LinkedIn → pick `linkedin_voice` (Amber Brand / Madhur / Jools)
- If Blog → pick `blog_lens` (Supply / University / HEA)

### 3️⃣ Generate Content
```
Click generation buttons → Wait 1-5 min each
```

**Order matters:**
- Run **Newsroom** first if you want **Newsletter**
- Newsletter curates from newsroom items

### 4️⃣ Review Content
```
Open Google Sheet → Check draft tabs
```

**Tabs:**
- Newsroom Blog (7-12 items per region)
- LinkedIn Drafts (15 posts)
- Blog Drafts (3 posts)
- Newsletter (1 draft)

---

## 🔄 Multiple Cycles

**Starting a new cycle automatically:**
- ✅ Archives previous data to Archive tabs
- ✅ Clears active tabs
- ✅ Preserves history in Cycles tab
- ✅ No data loss

**Archive tabs:**
- Archive - Signals
- Archive - Ranked Topics
- Archive - Newsroom Blog

**Find old data:** Filter by `cycle_id` or `cycle_date`

---

## ⚠️ Common Issues

### "All signals filtered out"
→ Check Signals tab `status` column
→ Adjust filters in `config/topic-rules.json`

### "No topics tagged for [channel]"
→ Open Sheet → Set `decision` to Approve
→ Add channel to `channels` column

### "Newsletter returned no content"
→ Run Newsroom Blog first
→ Then run Newsletter

### Progress stuck
→ Check terminal for errors
→ Restart: `python src/main.py`
→ Check Errors tab in Sheet

---

## 📊 What Gets Generated

### Newsroom Blog (Weekly)
- 7-12 items per region
- 21-25 words each
- Covers: UK, USA, Australia, Canada, Europe, Global

### LinkedIn Posts
- 5 topics × 3 voices = 15 posts
- Voices: Amber Brand, Madhur Gujar, Jools Horton-Lakins
- 150-300 words each

### Blog Posts
- 3 posts with different lenses
- Lenses: Supply, University, HEA
- 800-1200 words each

### Newsletter (Bimonthly)
- Curated from newsroom blog items
- 2 variants: Market Watch + amber Beat
- Editor's Choice + Top Global News

---

## 📁 Key Files

**Web Interface:**
- `static/index.html` — Control panel

**Configuration:**
- `config/sources.json` — RSS feeds
- `config/topic-rules.json` — Filtering rules
- `config/voices/` — Voice profiles
- `.env` — API keys and credentials (Slack, OpenAI, Google)

**Documentation:**
- `docs/12-web-interface-guide.md` — Full guide
- `docs/13-slack-integration.md` — Slack setup
- `docs/11-amber-beat-sop.md` — Newsroom SOP
- `docs/09-full-specification.md` — Complete spec

**Scripts:**
- `src/main.py` — Start server
- `test_slack.py` — Test Slack integration
- `run_phase1.py` — CLI for Phase 1
- `run_phase2.py` — CLI for Phase 2

---

## 🎯 Status: READY FOR PRODUCTION

✅ Web interface fully functional  
✅ All latest enhancements integrated  
✅ Automatic cycle archiving  
✅ Multi-cycle support  
✅ Real-time progress updates  
✅ Error handling and recovery  

⚠️ Known limitations (don't affect core functionality):
- Google Docs review URL (placeholder)
- Slack notifications (stubbed)
- Publishing APIs (Phase 3 not started)

---

## 📞 Support

**Logs:**
- Terminal output (real-time)
- Google Sheet → Errors tab
- Google Sheet → Cycles tab (history)

**Docs:**
- `docs/12-web-interface-guide.md` — Complete guide
- `docs/08-insights-and-issues.md` — Known issues
- `docs/03-progress-tracker.md` — Development status
