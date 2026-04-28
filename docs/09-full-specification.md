# Full System Specification

*This is the complete original specification document for reference.*

---

## 1. Problem Statement

Amber's marketing team needs to produce high-quality, data-led content every two weeks across three channels (LinkedIn, Blog, Newsletter), targeting three distinct stakeholder audiences (Supply Partners, Universities/HE, HEA/Agents), across four regions (UK, USA, Australia, Europe).

Today this is done manually: someone reads industry sources, picks topics, writes drafts, gets them reviewed, and publishes. This process is slow (takes days), inconsistent (depends on who's doing it), and doesn't scale as the team grows or the publication frequency increases.

The goal is to build an automated content pipeline that:
- Monitors relevant industry sources continuously
- Selects and ranks topics using editorial rules
- Generates channel-specific, audience-specific content drafts using AI
- Routes all content through human review at the right moments
- Publishes approved content to the right destinations
- Learns from performance data to improve future cycles

The system must be fully traceable — every piece of content must be linked back to the source signal that triggered it. Every human decision must be logged. Every AI output must be auditable.

## 2. System Overview

The system runs in recurring cycles (bi-monthly). Each cycle produces:
- 15 LinkedIn post drafts (5 topics x 3 voices)
- 3 blog post drafts (one per stakeholder audience)
- 1 newsletter draft (4 regional sections)

Total: 19 pieces of content per cycle, reviewed once, published to three channels.

Two human review gates per cycle:
1. Topic approval gate — after topic ranking, before any content is written
2. Content review gate — after all drafts are generated, before publishing

Everything between those gates is automated. Everything outside them is human-controlled.

## 3. Core Data Entities

### 3.1 Signal
signal_id, source_name, source_url, headline, summary, published_date, region (UK|USA|Australia|Europe|Global), topic_category (Rent Trends|Visa Data|Student Demand|Policy Changes|Supply Outlook|Emerging Markets|QS Rankings|Other), raw_content, captured_at, cycle_id

### 3.2 Topic
topic_id, cycle_id, title (max 10 words), summary (2-3 sentences), rank (1-5), urgency (Breaking|Time-sensitive|Evergreen), primary_region, secondary_regions[], stakeholder_tags[] (Supply|University|HEA), source_signal_ids[], rationale, status (Pending|Approved|Edited|Rejected), approved_by, approved_at, edited_title, edited_summary

### 3.3 ContentDraft
draft_id, cycle_id, topic_id, channel (LinkedIn|Blog|Newsletter), audience (Supply|University|HEA|All), voice (AmberBrand|Madhur|Jools|Supply|University|HEA|Global), content_body, word_count, generation_prompt, generation_model, generated_at, status (Draft|UnderReview|RevisionRequested|Approved|Published), review_comments, revised_body, revised_at, published_at, published_url

### 3.4 Cycle
cycle_id (e.g. "2025-W15"), started_at, stage (1-6), status (Running|AwaitingTopicApproval|AwaitingContentReview|Complete|Failed|Cancelled), topics_approved_at, content_approved_at, completed_at, error_log[], signal_count, topic_count, draft_count

### 3.5 ReviewSession
session_id, cycle_id, gate (TopicApproval|ContentReview), reviewer_name, started_at, completed_at, decisions[] ({item_id, action, comment})

## 4. Stage-by-Stage Flows

### Stage 1 — News Ingestion

Sources: HESA, UCAS, Home Office, Knight Frank, ICEF Monitor, IIE, DHA, Bonard, JLL, StuRents, Cushman & Wakefield, Enroly, Migration Advisory Committee, PIE News, Unipol, Property Week, PBSA News, QS Rankings, Google News

Flow:
1. Fetch content from each source (RSS, sitemap, web fetch)
2. Dedup against previous cycles by URL
3. Extract headline, body, date, source, URL
4. Recency check (news: 30 days, reports: 12 months)
5. AI tags: region, category, summary, negative/competitor/sensitive flags
6. Save as Signal with status=Captured
7. Unconfident tags → category="Other", flag for triage

Error handling: Source unreachable → skip. No new content → log. AI fail → save as TaggingFailed.

### Stage 2 — Topic Selection

Flow:
1. Load all signals from current cycle
2. Apply always-cover boost, never-cover discard, seasonal boost
3. Apply negative news protocol, sensitive topic escalation, competitor check
4. Score on: Urgency (1-10), Regional relevance (1-10), Stakeholder fit (1-10)
5. Group related signals into single topics
6. Produce ranked longlist of 10-15 topics with title, summary, urgency, stakeholders, regions, rationale
7. Save all as Topics with status=Pending

### Stage 3 — Shortlisting

Flow:
1. Apply stakeholder matrix (which audiences care about each topic)
2. Apply region relevance tags
3. Select top 5 ensuring: regional balance, category diversity, urgency ordering
4. Add content guidance note per topic
5. Save/update Topics with status=Pending

### Human Gate 1 — Topic Approval

Reviewer sees: Topic Approval Brief (5 topics with sources, rationale, longlist)
Actions: Approve all / Edit / Swap / Reject / Pause
Deadline: 12h reminder, 24h escalation, 48h auto-pause
Logging: ReviewSession created with all decisions

### Stage 4A — LinkedIn Agent (15 posts)

3 voices x 5 topics:
- Amber Company Page: authoritative, data-led, "we", 150-200w, 3-5 hashtags
- Madhur: bold, personal, "I", 150-250w, no hashtags
- Jools: thoughtful, HE insider, "I", 150-250w, no hashtags

Validation: word count, voice pronoun check, hashtag rules, character limit, similarity check
Auto-revision: 1 attempt if flagged

### Stage 4B — Blog Writer Agent (3 posts)

3 stakeholder lenses, top 3 topics:
- Supply: operator-forward, practical, 600-900w
- University: policy-aware, strategic, 600-900w
- HEA/Agents: market intelligence, practical, 600-900w

Validation: word count, headings present, data cited, CTA present

### Stage 4C — Newsletter Agent (1 draft)

4 regional sections (UK, USA, AU, Europe):
- Each: 3 sentences + 1 data point
- Header theme line, footer from config
- Under 500 words total

### Stage 5 — Review Document Assembly

Compile all 19 drafts into structured review doc → Google Drive → Slack notification

### Human Gate 2 — Content Review

Per-draft: [APPROVED] / [NEEDS EDIT] + comment / [BLOCK] + reason
Revision: Max 2 rounds, AI incorporates comments
Deadline: 24h reminder, 48h escalation, 72h auto-pause

### Stage 6 — Publishing

6A LinkedIn: Stagger by voice (1/day), queue to Buffer/LinkedIn API, human confirms schedule
6B Blog: Format for CMS, push as draft, human adds image + publishes
6C Newsletter: Format for email tool, push as draft, human confirms + sends

### Stage 7 — Performance Feedback

7 days post-publish: Pull LinkedIn engagement, email metrics
Calculate topic performance scores → write back to Topic store
Generate Cycle Performance Report → send to Slack
Scores influence next cycle's topic ranking (soft signal)

## 5. Configuration Store

- Editorial Rules: always-cover, never-cover, negative news, seasonal triggers, competitor list
- Voice Profiles: 6 voices (AmberBrand, Madhur, Jools, BlogSupply, BlogUniversity, BlogHEA) with tone, format, length, examples
- Source Configuration: 22 sources with URL, fetch method, region, priority, active toggle
- Publishing Configuration: LinkedIn accounts, posting schedule, hashtag library, CMS details, newsletter tool
- Notification Configuration: Slack channels, reviewer names, escalation contacts, deadlines

## 6. Logging & Traceability

Every action produces a log entry: log_id, cycle_id, stage, event_type, entity_type, entity_id, actor, timestamp, details (JSON)

Traceability chain: Published content → draft → topic → signals → source URLs → cycle ID → approver → reviewer

## 7. Error States & Recovery

- Source fetch failure → skip, continue
- AI generation failure → retry once, then flag
- Validation failure after 2 revisions → include with FLAGGED status
- Gate timeout → reminders, escalation, auto-pause
- Publishing API failure → retry 3x with backoff, then notify for manual publish
- Cycle crash → resume from last completed stage

## 8. Phase Delivery Plan

**Phase 1 (Weeks 1-3)**: Research + Topic Engine — Stages 1-3, Gate 1, logging, basic dashboard
**Phase 2 (Weeks 4-6)**: Content Generation + Review — Stages 4A-C, Stage 5, Gate 2, review interface
**Phase 3 (Weeks 7-9)**: Publish + Feedback — Stages 6A-C, Stage 7, publishing view, performance reports
