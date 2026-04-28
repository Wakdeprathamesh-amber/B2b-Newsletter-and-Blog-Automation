# B2B Newsletter and Blog Automation

Automated content generation system for Amber's B2B marketing - produces weekly newsletters, LinkedIn posts, blog articles, and newsroom updates from curated industry signals.

## Overview

This system automates the Amber Beat content pipeline:
- **Phase 1**: Scrapes 200+ signals from RSS feeds and Google News, filters and ranks into 40+ topics
- **Human Review**: Editorial team reviews and tags topics in Google Sheets
- **Phase 2**: Generates content across 4 channels (Newsroom, LinkedIn, Blog, Newsletter)

## Features

- 🔍 **Multi-source scraping**: RSS feeds + Google News with intelligent deduplication
- 🤖 **AI-powered ranking**: Parallel per-region LLM calls for topic selection
- 📊 **Google Sheets integration**: Full workflow visibility and human-in-the-loop review
- 💬 **Slack notifications**: Real-time progress updates and error alerts
- 🌐 **Web interface**: Control panel for cycle management and content generation
- 📝 **Multi-channel content**: Newsroom blog, LinkedIn posts, long-form blogs, newsletter

## Quick Start

See [QUICK-START.md](QUICK-START.md) for detailed setup instructions.

```bash
# 1. Install dependencies
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys and credentials

# 3. Setup Google Sheet
python3 setup_sheet.py

# 4. Start the server
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Open http://localhost:8000 to access the web interface.

## Documentation

- [Quick Start Guide](QUICK-START.md) - Get up and running
- [Setup Instructions](SETUP-INSTRUCTIONS.md) - Detailed configuration
- [Slack Integration](docs/13-slack-integration.md) - Notification setup
- [System Architecture](docs/02-system-architecture.md) - Technical overview
- [Full Specification](docs/09-full-specification.md) - Complete system spec

## Project Structure

```
├── src/
│   ├── api/              # FastAPI routes (web + UI)
│   ├── graph/            # LangGraph pipeline nodes
│   ├── integrations/     # Google Sheets, Slack
│   ├── models/           # Data schemas and enums
│   ├── scrapers/         # RSS, Google News, Firecrawl
│   └── main.py           # FastAPI app entry point
├── config/               # Editorial rules, sources, voices
├── prompts/              # LLM prompts for content generation
├── docs/                 # Documentation
└── static/               # Web interface HTML
```

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, LangGraph
- **LLM**: OpenAI GPT-4
- **Storage**: SQLite (local), Google Sheets (collaborative)
- **Integrations**: Google Sheets API, Slack API, Firecrawl
- **Scraping**: feedparser (RSS), httpx (Google News)

## Workflow

### Phase 1: Signal Collection & Ranking (Automated)
1. Archive previous cycle data
2. Scrape 200+ signals from RSS feeds and Google News
3. Filter out PR, opinion pieces, irrelevant content
4. Rank into 40+ topics (7-12 per region) using parallel LLM calls
5. Write to "Ranked Topics" tab in Google Sheets

### Human Review (Manual)
1. Review topics in Google Sheets "Ranked Topics" tab
2. Set decision (Approve/Reject/Edit)
3. Tag channels (Newsroom, LinkedIn, Blog, Newsletter)
4. Select voice/lens for LinkedIn and Blog content

### Phase 2: Content Generation (Automated)
1. Generate Newsroom blog items (3-sentence summaries)
2. Generate LinkedIn posts (3 voices × selected topics)
3. Generate long-form blog posts (3 lenses × selected topics)
4. Generate newsletter (curated from newsroom items)

## Configuration

Key configuration files:
- `.env` - API keys, credentials, feature flags
- `config/sources.json` - RSS feeds and scraping sources
- `config/editorial-guardrails.json` - Content filtering rules
- `config/stakeholders.json` - Audience definitions
- `config/voices/` - Voice and tone guidelines

## Requirements

- Python 3.11+
- OpenAI API key
- Google Cloud service account (for Sheets API)
- Slack bot token (optional, for notifications)
- Firecrawl API key (optional, for enhanced scraping)

## License

Proprietary - Amber Student Housing Ltd.

## Support

For issues or questions, contact the Amber marketing team.
