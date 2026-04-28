# Search, Scraping & Data Collection Strategy

*Meeting prep doc — covers tools, APIs, strategies, open questions, and what we need from the team*

---

## 1. The Core Problem

Stage 1 of the pipeline needs to **find and extract** fresh content from 22+ sources every cycle. Each source is different — some have RSS feeds, some are static web pages, some publish PDF reports, some need keyword search to discover. There is no single tool that handles all of them.

We need a **layered strategy** that combines multiple approaches.

---

## 2. Three Search/Discovery Strategies

### Strategy A: Source Monitoring (Known Sources)
Go directly to our 22 configured sources and check for new content.

- **How**: RSS feeds where available, web scraping where not
- **Pros**: High quality, predictable, low noise, stays within our trusted source list
- **Cons**: Misses breaking news from sources we don't monitor, blind to new/emerging sources
- **Cost**: Low (mostly free tools)

### Strategy B: Keyword/Topic Search (Discovery)
Search the open web for relevant keywords like "international student visa UK 2026", "PBSA occupancy rates", "student accommodation rent data".

- **How**: Google News RSS (free), Tavily API, or Brave Search API
- **Pros**: Catches breaking news from ANY source, discovers sources we don't know about
- **Cons**: Noisy — needs filtering, may surface low-quality or irrelevant results
- **Cost**: Low-Medium (free with Google News RSS, or $3-50/mo with APIs)

### Strategy C: AI-Powered Research (Deep Search)
Use AI search tools (Claude web search, Perplexity) to ask research questions and get synthesized answers with citations.

- **How**: Claude's built-in web search, Perplexity API, or Tavily with AI summary
- **Pros**: Gets the "so what" along with the data, finds context and connections humans would
- **Cons**: More expensive per query, harder to control, may hallucinate or miss things
- **Cost**: Medium (per-token pricing)

### RECOMMENDED: Strategy A + B + C (Layered)

```
Layer 1 (Backbone): Source Monitoring
  Check all 22 known sources via RSS + scraping
  Runs every cycle, catches ~70% of relevant signals
  
Layer 2 (Discovery): Keyword Search  
  Search Google News + Brave/Tavily for curated keywords
  Catches breaking news and stories from unknown sources
  Adds ~20% more signals

Layer 3 (Deep Dive): AI Research
  Use Claude web search or Perplexity for specific research questions
  E.g. "What are the latest UK student visa statistics Q1 2026?"
  Fills gaps and adds context — ~10% more signals
```

---

## 3. Tool Landscape — What Exists

### Search APIs

| Tool | Free Tier | Paid From | Python SDK | Best For |
|------|-----------|-----------|------------|----------|
| **Tavily** | 1,000/mo | ~$50/mo | Yes | AI-optimized search, built for agents |
| **Exa.ai** | 1,000/mo | ~$50/mo | Yes | Semantic "find similar" content discovery |
| **Perplexity API** | None | Pay-per-token | Yes | Synthesized answers with citations |
| **SerpAPI** | 100/mo | $50/mo | Yes | Raw Google Search results |
| **Brave Search** | 2,000/mo | $3/mo | No (REST) | Cheapest search API with news endpoint |
| **Google Custom Search** | 100/day | $5/1K queries | Yes | Official Google, site-scoped search |
| **Bing News API** | 1,000/mo | ~$3/1K calls | Yes | News-specific search + trending |
| **Claude Web Search** | Included with API | Part of Claude usage | Yes (MCP) | Deep research questions |

### Scraping / Content Extraction

| Tool | Free Tier | Paid From | Python SDK | Best For |
|------|-----------|-----------|------------|----------|
| **Firecrawl** | 500 pages/mo | $19/mo | Yes | Best all-round web-to-markdown |
| **Jina Reader** | ~1,000/day | $9.90/mo | No (HTTP GET) | Simplest — just prepend URL |
| **Apify** | $5 credits/mo | $49/mo | Yes | Complex multi-page scraping |
| **ScrapingBee** | 1,000 one-time | $49/mo | Yes | Sites that block scrapers |
| **Diffbot** | 14-day trial | $299/mo | Yes | Enterprise — overkill for us |
| **BeautifulSoup** | Free (open source) | Free | IS the SDK | Custom HTML parsing |

### News APIs

| Tool | Free Tier | Paid From | Python SDK | Best For |
|------|-----------|-----------|------------|----------|
| **Google News RSS** | Unlimited, free | Free | feedparser | Zero-cost news headlines |
| **GNews API** | 100/day | $7/mo | No | Budget Google News alternative |
| **Newsdata.io** | 200/day | $25/mo | Yes | International coverage |
| **NewsAPI.org** | 100/day (non-commercial) | $449/mo | Yes | Broad but expensive |

### PDF / Report Extraction

| Tool | Free Tier | Python SDK | Best For |
|------|-----------|------------|----------|
| **pdfplumber** | Open source (MIT) | Yes | Tables from PDF reports |
| **PyMuPDF (fitz)** | Open source (AGPL) | Yes | Fast general text extraction |

### RSS Parsing

| Tool | Cost | Notes |
|------|------|-------|
| **feedparser** | Free, open source | Standard Python RSS parser, rock-solid |

---

## 4. Recommended Tool Stack

### Must-Have (Core)

| Purpose | Tool | Cost | Why |
|---------|------|------|-----|
| RSS parsing | **feedparser** | Free | Handles RSS/Atom feeds from ICEF, PIE News, etc. |
| Web scraping | **Firecrawl** | $19/mo | Converts any page to clean markdown for Claude |
| News search | **Google News RSS** | Free | Keyword-based news discovery, zero cost |
| PDF extraction | **pdfplumber** | Free | Extract data from Knight Frank, HESA PDF reports |
| AI tagging | **Claude API** (Sonnet) | Per-token | Already in our stack — tags signals |

### Should-Have (Recommended)

| Purpose | Tool | Cost | Why |
|---------|------|------|-----|
| AI search | **Tavily** | Free tier (1K/mo) | Purpose-built for AI agents, clean results |
| Backup search | **Brave Search** | $3/mo | Cheap, good news endpoint, wide coverage |
| Deep research | **Claude Web Search** | Part of API | Answer specific research questions with citations |
| Backup scraping | **Jina Reader** | Free tier | Dead simple fallback if Firecrawl fails |

### Nice-to-Have (Later)

| Purpose | Tool | Cost | Why |
|---------|------|------|-----|
| Semantic discovery | **Exa.ai** | Free tier | "Find articles similar to this one" |
| International news | **Newsdata.io** | $25/mo | Better non-English/non-UK coverage |
| Change detection | Custom script | Free | Monitor pages that don't have RSS for new content |

### Estimated Monthly Cost

| Tier | Tools | Monthly Cost |
|------|-------|-------------|
| **Minimum viable** | feedparser + Firecrawl + Google News RSS + pdfplumber | ~$19/mo |
| **Recommended** | Above + Tavily + Brave Search + Jina Reader | ~$72/mo |
| **Full stack** | Above + Exa + Newsdata.io | ~$147/mo |

*(Plus Claude API usage which you're already paying for)*

---

## 5. Source-by-Source Fetch Strategy

### Sources WITH RSS Feeds (easiest)

| Source | RSS Feed | Strategy |
|--------|----------|----------|
| ICEF Monitor | `https://monitor.icef.com/feed/` | feedparser — parse on each cycle |
| The PIE News | `https://thepienews.com/feed/` | feedparser — parse on each cycle |
| Property Week | Likely has feed | feedparser — need to verify URL |
| PBSA News | Likely has feed | feedparser — need to verify URL |

**Effort**: Low. Just parse RSS, extract title + link + date + summary, then scrape full article if needed.

### Sources That Need Web Scraping

| Source | What to Scrape | Strategy |
|--------|---------------|----------|
| HESA | News/data releases page | Firecrawl → scrape updates page, diff for new items |
| UCAS | Data and analysis page | Firecrawl → scrape, may also have RSS (verify) |
| Home Office | Immigration statistics page | Firecrawl → scrape GOV.UK stats releases |
| Knight Frank | Research/insights page | Firecrawl → scrape research listings |
| JLL | Research page | Firecrawl → scrape insights/research section |
| Savills | Research page | Firecrawl → scrape student housing research |
| Cushman & Wakefield | Insights page | Firecrawl → scrape insights section |
| Bonard | News/insights | Firecrawl → scrape (may need to check structure) |
| StuRents | Data/reports page | Firecrawl → scrape rent index updates |
| Enroly | Blog/insights | Firecrawl → scrape blog section |
| Unipol | News/resources | Firecrawl → scrape publications page |
| DHA Australia | Statistics page | Firecrawl → scrape visa stats releases |
| MAC | Reports page | Firecrawl → scrape GOV.UK publications |
| IIE | Open Doors data page | Firecrawl → scrape when data released |

**Effort**: Medium. Each source needs its target URL(s) identified. Firecrawl handles the rendering and extraction.

### Sources That Publish PDF Reports

| Source | Report Type | Strategy |
|--------|------------|----------|
| Knight Frank | PBSA market reports | Firecrawl for landing page → download PDF → pdfplumber to extract |
| HESA | Statistical bulletins | Same — scrape page, download PDF, extract data |
| JLL | Market outlook reports | Same pattern |
| Savills | Student housing reports | Same pattern |
| Bonard | PBSA market intelligence | Same pattern |

**Effort**: Medium-High. Need PDF download + extraction pipeline.

### Keyword Search (Discovery Layer)

| Search Term | Region | Source |
|-------------|--------|--------|
| "international student visa" + [UK/USA/Australia] | Per region | Google News RSS |
| "student accommodation rent" | UK, AU | Google News RSS |
| "PBSA occupancy rates" | Global | Google News RSS / Tavily |
| "international student enrolment data" | Per region | Google News RSS |
| "student housing supply pipeline" | UK | Google News RSS |
| "international education policy" | Per region | Google News RSS |
| "student visa rejection" | Per region | Google News RSS |
| "university international recruitment" | Global | Google News RSS |

**Effort**: Low. Construct RSS URLs with keywords, parse with feedparser. Need to curate and refine keyword list.

### AI Deep Research (Gap-Filling Layer)

| Research Question | When to Ask | Tool |
|-------------------|-------------|------|
| "What are the latest UK student visa statistics?" | Every cycle | Claude Web Search / Tavily |
| "Any new PBSA developments announced this month?" | Every cycle | Claude Web Search |
| "What policy changes affect international students in [region]?" | Every cycle | Claude Web Search |
| "Latest university ranking movements?" | When QS/THE release | Claude Web Search |

**Effort**: Low. These are Claude API calls with web search enabled.

---

## 6. The Fetch Pipeline (How It All Fits Together)

```
CYCLE STARTS
    │
    ├── [Parallel] Layer 1: Source Monitoring
    │   ├── RSS Sources → feedparser → extract items
    │   ├── Web Sources → Firecrawl → scrape pages → extract items  
    │   └── PDF Sources → Firecrawl + pdfplumber → extract data
    │
    ├── [Parallel] Layer 2: Keyword Search
    │   ├── Google News RSS → feedparser → extract headlines
    │   └── (Optional) Tavily/Brave → search API → extract results
    │
    ├── [Parallel] Layer 3: AI Research
    │   └── Claude Web Search → targeted questions → extract findings
    │
    ▼
    DEDUP (by URL, against previous cycles)
    │
    ▼
    RECENCY CHECK (news: 30 days, reports: 12 months)
    │
    ▼
    AI TAGGING (Claude Sonnet — region, category, flags)
    │
    ▼
    SIGNALS READY → Stage 2 (Topic Selection)
```

---

## 7. API Keys & Credentials Needed

### Definitely Need (for recommended stack)

| Service | What You Need | Where to Get It | Est. Cost |
|---------|--------------|-----------------|-----------|
| **Anthropic (Claude)** | API key | console.anthropic.com | Already have |
| **Firecrawl** | API key | firecrawl.dev/app/sign-up | $19/mo |
| **Tavily** | API key | app.tavily.com | Free tier / $50/mo |

### Should Get

| Service | What You Need | Where to Get It | Est. Cost |
|---------|--------------|-----------------|-----------|
| **Brave Search** | API key | brave.com/search/api | Free tier / $3/mo |

### Will Need for Publishing (Phase 3, not yet)

| Service | What You Need | Where to Get It |
|---------|--------------|-----------------|
| **Slack** | Bot token + channel IDs | api.slack.com/apps |
| **Google** | Service account JSON (for Google Docs) | console.cloud.google.com |
| **LinkedIn** | Marketing API access token | linkedin.com/developers |
| **Buffer** (alternative) | Access token | buffer.com/developers |
| **HubSpot** | API key | developers.hubspot.com |
| **Notion** (for blog CMS) | Integration token | notion.so/my-integrations |

### Free / No Key Needed

| Tool | Notes |
|------|-------|
| feedparser | Python library, just `pip install` |
| Google News RSS | No auth, just construct URL |
| pdfplumber | Python library, just `pip install` |
| Jina Reader | Works without key (rate-limited), key optional |
| BeautifulSoup | Python library |

---

## 8. MCP Servers (Claude Code Integration)

These MCP servers could be useful for development and can be added to Claude Code's config:

| MCP Server | Purpose | When Useful |
|------------|---------|-------------|
| **Slack MCP** | Send/read Slack messages directly | Testing notifications |
| **Google Drive MCP** | Create/read Google Docs | Testing review doc creation |
| **Notion MCP** | Create/read Notion pages | Testing blog publishing |
| **Gmail MCP** | Send emails | Testing newsletter flow |
| **Airtable MCP** | Structured data storage | Alternative to Google Sheets for signal storage |

---

## 9. QUESTIONS FOR THE TEAM

### Sources & Fetching

1. **Do you currently subscribe to any of these sources?** (e.g. Knight Frank reports, Bonard data) — some may require login/subscription to access full content
2. **Are there paywalled sources?** Which of the 22 sources require a paid subscription to access full articles/reports?
3. **IHEC and PBSA News have no URLs in our config** — can you provide the correct website URLs?
4. **Are there sources missing from our list?** Any that you read regularly that we haven't included?
5. **Do you receive email newsletters from any sources?** (e.g. Knight Frank sends market updates via email) — we could potentially parse those too
6. **Google News as a source** — currently listed as "low priority gap filler". Should it be higher? It catches things specialist outlets miss.

### Content & Quality

7. **What does "good enough" look like for signal capture?** Is it okay if we miss ~10-15% of relevant articles per cycle, as long as we catch the important ones? Or does it need to be exhaustive?
8. **How much raw content do you need per signal?** Full article text, or is headline + 3-sentence summary + URL sufficient for topic selection?
9. **PDF reports** — some sources (Knight Frank, HESA, JLL) publish data as PDFs. Do we need to extract data from these, or is it enough to capture "Knight Frank published Q1 PBSA report" as a signal and link to the PDF?

### Keywords & Search

10. **What terms would YOU search for** when looking for content? List the exact Google searches you'd type — these become our keyword search queries.
11. **Any specific hashtags or LinkedIn accounts you follow** for industry news? These could become additional signal sources.
12. **Amber's own content** — should we monitor what amber has already published to avoid duplication or to measure performance? If so, what are the URLs (LinkedIn page, blog, newsletter archive)?

### Competitors & Sensitive Topics

13. **Who are the competitors we must never mention?** The config says "no competitor brands" — we need the specific names to filter them out.
14. **Escalation contact** — who should be the named reviewer for sensitive topics? (Currently TODO in the guardrails config)

### Regions

15. **Region weighting** — should all 4 regions get equal attention, or is UK the primary market? If UK is primary, what's the rough split? (e.g. 40% UK, 20% USA, 20% AU, 20% EU?)
16. **Europe** — which countries specifically? EU is broad. Are we mainly watching Germany, Netherlands, France? Or all of EU?
17. **Any new regions to add?** Canada, Middle East, Southeast Asia, India — any of these becoming important for amber?

### Workflow & Preferences

18. **How often should cycles run?** Currently set to bi-monthly (every 2 weeks). Is that right, or should it be weekly? Monthly?
19. **Who are the reviewers for Gate 1 (topic approval)?** Names and Slack handles.
20. **Who are the reviewers for Gate 2 (content review)?** Names and Slack handles.
21. **Where should the review document live?** Google Docs? Notion? A custom web UI? Slack thread?
22. **What's your current publishing stack?** Which tools do you actually use for: LinkedIn scheduling, blog CMS, email newsletters?

### Budget & Priority

23. **What's the budget for tools/APIs?** This helps us choose between budget ($19/mo) and recommended ($72/mo) tool stacks.
24. **What's more important: breadth (catch everything) or precision (only high-quality signals)?** This determines how aggressive we are with keyword search.
25. **Timeline** — when does the team want to start using this for real (not dev mode)?

---

## 10. Decision Matrix — What We Need Answered

| Decision | Options | Impact | Who Decides |
|----------|---------|--------|-------------|
| Search strategy | A only / A+B / A+B+C | How many signals we catch | Team + Engineering |
| Scraping tool | Firecrawl / Jina / Both | Reliability & cost | Engineering |
| News search tool | Google News RSS / Tavily / Brave / Multiple | Coverage vs cost | Team (budget) |
| PDF handling | Extract data / Just link to PDF | Complexity vs signal quality | Team (content need) |
| AI research layer | Claude search / Perplexity / Skip | Cost vs signal depth | Team (budget) |
| Review doc format | Google Docs / Notion / Custom UI | UX for reviewers | Team (preference) |
| Publishing tools | Buffer/LinkedIn + Notion + HubSpot | Phase 3 integrations | Team (existing stack) |
| Competitor list | Need specific names | Content filtering accuracy | Team (must provide) |
| Region priority | Equal / UK-heavy / Custom split | Topic selection weighting | Team (strategy) |
| Cycle frequency | Weekly / Bi-weekly / Monthly | Pipeline load & content volume | Team (marketing calendar) |

---

## 11. Next Steps After the Meeting

1. **Collect API keys** for: Firecrawl, Tavily (and any others decided)
2. **Get answers** to the 25 questions above
3. **Verify RSS feeds** — check which of the 22 sources actually have working feeds
4. **Map scraping targets** — for non-RSS sources, identify the exact URLs to monitor
5. **Build keyword list** — from team's input, create the search queries for Layer 2
6. **Fill in config gaps** — competitor names, escalation contact, IHEC/PBSA News URLs
7. **Implement `_fetch_source()`** — the main production blocker
