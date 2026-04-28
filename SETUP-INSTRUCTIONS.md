# Setup Instructions — Amber Content Engine

Complete setup guide from scratch.

---

## 1. Python Virtual Environment

### Create Virtual Environment

```bash
python3 -m venv venv
```

### Activate Virtual Environment

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -e .
```

Or install manually:
```bash
pip install slack-sdk pydantic pydantic-settings python-dotenv structlog \
    openai anthropic langgraph langchain-anthropic langsmith \
    sqlalchemy alembic psycopg[binary] langgraph-checkpoint-postgres \
    fastapi uvicorn[standard] \
    firecrawl-py feedparser httpx \
    gspread google-auth hubspot-api-client apscheduler tenacity
```

---

## 2. Environment Variables

### Copy Example File

```bash
cp .env.example .env
```

### Configure `.env`

Edit `.env` and add your credentials:

```bash
# ─── LLM ───
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-your-key-here
GENERATION_MODEL=gpt-4o
EDITORIAL_MODEL=gpt-4o
DEV_MODE=false

# ─── Scraping ───
FIRECRAWL_API_KEY=fc-your-key-here

# ─── Google (Sheets + Docs) ───
GOOGLE_SERVICE_ACCOUNT_JSON=credentials/your-service-account.json
GOOGLE_MASTER_SHEET_ID=your-sheet-id-here

# ─── Slack ───
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_CHANNEL_ID=C0XXXXXXXXX
```

---

## 3. Google Sheets Setup

### Create Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable Google Sheets API
4. Create Service Account:
   - IAM & Admin → Service Accounts → Create
   - Download JSON key file
5. Save JSON file to `credentials/` folder
6. Update `.env` with the path

### Create Master Sheet

```bash
python setup_sheet.py
```

This creates a Google Sheet with all required tabs:
- Dashboard
- Cycles
- Signals
- Ranked Topics
- Shortlist
- LinkedIn Drafts
- Blog Drafts
- Newsletter
- Newsroom Blog
- Publishing Log
- Feedback
- Errors
- Reference
- Archive tabs

### Share Sheet with Service Account

1. Open the created Google Sheet
2. Click "Share"
3. Add the service account email (from JSON file)
4. Give "Editor" permissions

---

## 4. Slack Setup

### Create Slack App

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name your app (e.g., "Amber Content Engine")
4. Select your workspace

### Add OAuth Scopes

1. Go to **OAuth & Permissions**
2. Scroll to **Scopes**
3. Add these **Bot Token Scopes:**
   - `chat:write`
   - `chat:write.public`

### Install App to Workspace

1. Go to **OAuth & Permissions**
2. Click "Install to Workspace"
3. Authorize the app
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### Get Signing Secret

1. Go to **Basic Information**
2. Scroll to **App Credentials**
3. Copy the **Signing Secret**

### Create/Select Channel

1. Create a new channel (e.g., `#amber-notifications`)
2. Right-click channel → View channel details
3. Copy the **Channel ID** (e.g., `C0B01Q2BJF4`)

### Invite Bot to Channel

In the Slack channel, type:
```
/invite @YourBotName
```

### Update `.env`

```bash
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_SIGNING_SECRET=your-secret-here
SLACK_CHANNEL_ID=C0XXXXXXXXX
```

### Test Slack

```bash
source venv/bin/activate
python test_slack.py
```

Expected output:
```
✅ Test message sent successfully!
```

---

## 5. Test the System

### Check Setup

```bash
python check_setup.py
```

This verifies:
- ✅ Environment variables
- ✅ Google Sheets connection
- ✅ Slack connection
- ✅ LLM API keys
- ✅ Database connection

### Run Test Cycle

```bash
# Dev mode (no API calls, uses sample data)
DEV_MODE=true python run_test.py

# Production mode (real API calls)
python run_phase1.py --limit 10
```

---

## 6. Start the Server

### Development Mode

```bash
source venv/bin/activate
python src/main.py
```

Server starts at: `http://localhost:8000`

### Production Mode

```bash
source venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

---

## 7. Use the Web Interface

1. Open browser: `http://localhost:8000`
2. Click "Start New Cycle"
3. Wait 5-15 minutes
4. Open Google Sheet to review topics
5. Tag topics with channels
6. Generate content

**Slack notifications will appear automatically!**

---

## Troubleshooting

### Virtual Environment Not Activating

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

**Check if active:**
```bash
which python  # Should show path to venv/bin/python
```

### Module Not Found Errors

```bash
# Reinstall dependencies
pip install -e .
```

### Slack: `channel_not_found`

```bash
# Invite bot to channel
/invite @YourBotName
```

See `SLACK-TROUBLESHOOTING.md` for details.

### Google Sheets: Permission Denied

1. Open Google Sheet
2. Share with service account email
3. Give "Editor" permissions

### LLM API Errors

Check `.env`:
```bash
OPENAI_API_KEY=sk-proj-...  # Must start with sk-
```

Test:
```bash
python -c "from src.settings import settings; print(settings.is_llm_available)"
# Should print: True
```

---

## File Structure

```
.
├── .env                          # Your credentials (not in git)
├── .env.example                  # Template
├── venv/                         # Virtual environment (not in git)
├── credentials/                  # Google service account JSON
├── config/                       # Configuration files
│   ├── sources.json
│   ├── topic-rules.json
│   ├── stakeholders.json
│   └── voices/
├── src/                          # Source code
│   ├── main.py                   # FastAPI server
│   ├── settings.py               # Configuration
│   ├── integrations/
│   │   ├── sheets.py
│   │   └── slack.py
│   └── ...
├── static/
│   └── index.html                # Web interface
├── docs/                         # Documentation
├── test_slack.py                 # Slack test script
├── setup_sheet.py                # Google Sheet setup
├── run_phase1.py                 # CLI for Phase 1
└── run_phase2.py                 # CLI for Phase 2
```

---

## Quick Reference

### Activate Virtual Environment
```bash
source venv/bin/activate
```

### Test Slack
```bash
python test_slack.py
```

### Start Server
```bash
python src/main.py
```

### Run Phase 1 (CLI)
```bash
python run_phase1.py
```

### Run Phase 2 (CLI)
```bash
python run_phase2.py
```

### Check Setup
```bash
python check_setup.py
```

---

## Next Steps

1. ✅ Setup complete
2. ✅ Test Slack: `python test_slack.py`
3. ✅ Start server: `python src/main.py`
4. ✅ Open web interface: `http://localhost:8000`
5. ✅ Start a cycle and watch Slack notifications!

---

## Support

**Documentation:**
- `QUICK-START.md` — Quick reference
- `SLACK-TROUBLESHOOTING.md` — Slack issues
- `docs/12-web-interface-guide.md` — Web interface
- `docs/13-slack-integration.md` — Slack integration

**Test Scripts:**
- `test_slack.py` — Test Slack
- `check_setup.py` — Verify setup
- `run_test.py` — Test full pipeline

**Logs:**
- Terminal output (real-time)
- Google Sheet → Errors tab
