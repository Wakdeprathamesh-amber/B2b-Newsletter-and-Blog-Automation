# Stage-by-Stage Detail

## Stage 1 — Signal Ingestion

**Purpose**: Capture signals from 22 monitored sources, tag them by region/category, flag sensitive content.

**Sources**: HESA, UCAS, Home Office, Knight Frank, ICEF Monitor, IIE, DHA, Bonard, JLL, StuRents, Cushman & Wakefield, Enroly, Migration Advisory Committee, The PIE News, Unipol, Property Week, PBSA News, QS Rankings, Google News, Global Migration Data Portal, Savills, IHEC

**Recency Rules**:
- News articles: published within 30 days
- Reports/data: published within 12 months

**AI Tagging** (Claude Sonnet):
- Region: UK / USA / Australia / Europe / Global
- Category: Rent Trends / Visa Data / Student Demand / Policy Changes / Supply Outlook / Emerging Markets / QS Rankings / Other
- Flags: is_negative_news, mentions_competitor, is_politically_sensitive

**Error Handling**: Source unreachable → skip, continue. AI fails → save with `tagging_failed=True`.

---

## Stage 2 — Topic Selection

**Purpose**: Apply editorial rules to score and rank 10-15 candidate topics from signals.

**Filters Applied**:
1. Always-cover list → auto-boost to Priority High
2. Never-cover list → discard and log
3. Seasonal triggers → boost if relevant
4. Negative news protocol → reframe or discard
5. Sensitive topic check → escalation flag
6. Competitor mention check → incidental (ok) vs about competitor (discard)

**Scoring Dimensions**:
- Urgency (35%)
- Regional relevance (25%)
- Stakeholder fit (25%)
- Data quality (15%)

**Signal Grouping**: Related signals combined into single topic (e.g., 3 UK rent signals → 1 rent topic).

---

## Stage 3 — Shortlisting

**Purpose**: Select top 5 from longlist, ensuring balance.

**Balance Rules**:
- At least one topic per major region (UK, USA, AU) if signals exist
- Not all 5 from same category
- Topic 1 = most urgent; Topic 5 = evergreen backup
- Each topic tagged with: stakeholder audience(s), region(s), content guidance

---

## Human Gate 1 — Topic Approval

**Reviewer Actions**: Approve all / Approve with edits / Swap from longlist / Reject / Pause cycle

**Timeout**: 12h reminder → 24h escalation → 48h auto-pause

---

## Stage 4A — LinkedIn Agent (15 Posts)

**Voices**:
| Voice | Tone | Audience | Length | Hashtags |
|-------|------|----------|--------|----------|
| Amber Brand | Authoritative, data-led, "we" | Broad | 150-200w | 3-5 |
| Madhur | Bold, personal, "I" | Supply + HEI leadership | 150-250w | None |
| Jools | Thoughtful, HE insider, "I" | Universities + housing | 150-250w | None |

**Validation**: Word count, "I" vs "we" check, hashtag presence, character limit, similarity check.
**Auto-revision**: 1 attempt if validation fails.

## Stage 4B — Blog Agent (3 Posts)

**Lenses**:
| Audience | Tone | Reader | Key Terms |
|----------|------|--------|-----------|
| Supply | Operator-forward, practical | PBSA operators, asset mgrs | yield, occupancy, void periods |
| University | Policy-aware, strategic | Housing team, Dean, Intl Office | enrolment, compliance, partnerships |
| HEA/Agents | Market intelligence | Counsellors, franchise owners | recruitment corridor, visa conversion |

**Topic Assignment**: Each blog gets the topic most relevant to its audience (by stakeholder_tags).
**Validation**: 600-900 words, has headings, cites data, has CTA.

## Stage 4C — Newsletter Agent (1 Draft)

**Structure**: Header theme → UK section → USA section → Australia section → Europe section → Footer
**Per Section**: 3 sentences (What happened → Why it matters → What to watch) + 1 data point
**Validation**: Under 500 words, all 4 sections present, each cites a data point.

---

## Stage 5 — Review Document Assembly

Compiles all 19 drafts into a structured review document:
- Section 1: LinkedIn (15 posts grouped by topic)
- Section 2: Blogs (3 posts by audience)
- Section 3: Newsletter (1 draft)

Each draft shows: status, word count, validation flags, source signal.

---

## Human Gate 2 — Content Review

**Per-Draft Actions**: [APPROVED] / [NEEDS EDIT] + comment / [BLOCK] + reason
**Revision Loop**: Max 2 rounds. AI incorporates reviewer comments, sends back for re-review.
**Timeout**: 24h reminder → 48h escalation → 72h auto-pause

---

## Stage 6 — Publishing

- **LinkedIn**: Staggered schedule (1/day, by voice order within topics, ~10 business days)
- **Blog**: Push to CMS as draft → human adds image + publishes
- **Newsletter**: Push to email tool as draft → human confirms send list + sends

---

## Stage 7 — Feedback Loop

**Trigger**: 7 days after last publish
**Metrics**: LinkedIn engagement, email open/CTR, blog pageviews
**Output**: Performance scores per topic → feed into next cycle's ranking
