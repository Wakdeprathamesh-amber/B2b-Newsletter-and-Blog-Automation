"""Stage 1 -- News Ingestion Node.

Scrapes all configured sources, extracts content, uses Claude to tag each signal,
checks for duplicates, and stores structured Signal records.

In dev mode: returns sample signals without calling external APIs.
"""

import json
from datetime import datetime, timedelta, timezone

import structlog

from src.graph.state import PipelineState
from src.models.schemas import Signal
from src.models.enums import Region, TopicCategory
from src.settings import settings

log = structlog.get_logger()

SOURCE_CONFIG_PATH = "config/sources.json"

TAGGING_PROMPT = """You are a research extraction agent for amber, a company in the international student accommodation sector.

Analyze the following article/content and extract structured information.

CONTENT:
Source: {source_name}
URL: {url}
Headline: {headline}
Body: {body}

Return a JSON object with these fields:
- "region": one of "UK", "USA", "Australia", "Canada", "Europe", "Global"
- "topic_category": one of "Rent Trends", "Visa Data", "Student Demand", "Policy Changes", "Supply Outlook", "Emerging Markets", "QS Rankings", "Other"
- "summary": A data-rich factual briefing (3-5 sentences). You MUST extract and include every number, percentage, and monetary figure from the article. Structure it as:
    Sentence 1: Lead with the MAIN DATA POINT — a specific number (e.g. "UK visa grants fell 12% to 89,400 in Q1 2026").
    Sentence 2: SUPPORTING DATA — additional figures, YoY comparisons, rankings (e.g. "down from 101,600 in Q1 2025, driven by a 18% drop in Indian applicants").
    Sentence 3: MORE DATA if available — monetary values, percentages, counts (e.g. "Financial requirements increased by £2,800 to £11,502").
    Sentence 4: WHO is affected and HOW — practical implication for student accommodation sector.
    Sentence 5 (if relevant): What happens next — deadline, follow-up date, or forward signal.
  CRITICAL RULES:
  - Extract EVERY number from the article: percentages (%), monetary values (£, $, €, AUD), counts, dates, rankings
  - Never write "significant" or "substantial" — write the actual number
  - Never write "increased" without saying by how much
  - If the article contains no numbers at all, say "No specific data provided" at the start
  - The summary must be self-contained: a reader should understand the news WITHOUT reading the original article
- "is_negative_news": true/false — news that poses a risk, decline, or threat to the sector
- "mentions_competitor": true/false — mentions a direct competitor of amber by name
- "is_politically_sensitive": true/false — politically charged content requiring careful framing
- "is_opinion": true/false — true if this is an opinion piece, editorial, commentary, analyst prediction, or personal viewpoint rather than a factual news report or data release. Examples: op-eds, columns, "I think" articles, market predictions without data backing, expert commentary pieces.
- "is_pr_article": true/false — true if this is a PR/press release, promotional content, company announcement (e.g. "Company X launches new product", "Company X appoints new CEO", "Company X wins award"), marketing content, or sponsored content. These are NOT news.
- "is_relevant": true/false — true ONLY if the content genuinely relates to international students, student accommodation, higher education policy, student visas, PBSA, or university enrolment. Set false for: domestic-only education news, generic property news not about students, unrelated immigration news, corporate PR.
- "published_date": ISO date string if you can extract it, otherwise null

Rules:
- Be strict about relevance — only tag as relevant if clearly about international students and/or student accommodation
- If not relevant, set is_relevant to false and topic_category to "Other"
- Be factual and data-specific in the summary — always cite the actual numbers from the source
- If unsure about region, use "Global"

Return ONLY the JSON object, no other text."""


async def ingest_signals(state: PipelineState) -> dict:
    """Stage 1: Fetch, extract, tag, and store signals from all sources."""

    cycle = state.cycle
    errors: list[str] = []

    log.info("stage1_start", cycle_id=cycle.cycle_id)

    # -- Dev mode: return sample data --
    if settings.dev_mode or not settings.is_llm_available:
        from src.sample_data import get_sample_signals
        signals = get_sample_signals(cycle.cycle_id)
        log.info("stage1_complete_dev_mode", signal_count=len(signals))
        updated_cycle = cycle.model_copy(update={"signal_count": len(signals), "stage": 2})
        return {"signals": signals, "cycle": updated_cycle, "errors": errors}

    # -- Production mode --
    signals: list[Signal] = []
    signal_counter = 0

    # Load sources
    try:
        with open(SOURCE_CONFIG_PATH) as f:
            config = json.load(f)
        sources = config["sources"]
    except Exception as e:
        errors.append(f"Failed to load source config: {e}")
        log.error("source_config_failed", error=str(e))
        return {"signals": signals, "errors": errors}

    for source in sources:
        source_name = source["name"]
        source_url = source.get("url", "")

        if not source_url:
            log.info("source_skipped_no_url", source=source_name)
            continue

        try:
            raw_items = await _fetch_source(source)

            if not raw_items:
                log.info("source_no_new_content", source=source_name)
                continue

            for item in raw_items:
                if _is_duplicate(item["url"], cycle.cycle_id):
                    log.debug("signal_skipped_duplicate", url=item["url"])
                    continue

                if not _passes_recency_check(item, source):
                    log.debug("signal_skipped_recency", url=item["url"])
                    continue

                try:
                    tag_result = await _tag_with_llm(
                        source_name, item["url"], item["headline"], item["body"]
                    )

                    # Prefer the source_name reported by the fetcher (real publisher
                    # from Google News), falling back to the editorial source label.
                    signal_source = item.get("source_name") or source_name
                    signal_counter += 1
                    is_opinion = bool(tag_result.get("is_opinion", False))
                    is_pr = bool(tag_result.get("is_pr_article", False))
                    is_relevant = bool(tag_result.get("is_relevant", True))
                    mentions_comp = bool(tag_result.get("mentions_competitor", False))

                    # Determine status — filter out PR, opinion, irrelevant, competitor
                    if is_pr:
                        sig_status = "Dropped (PR)"
                    elif is_opinion:
                        sig_status = "Dropped (Opinion)"
                    elif not is_relevant:
                        sig_status = "Dropped (Irrelevant)"
                    elif mentions_comp:
                        sig_status = "Dropped (Competitor)"
                    else:
                        sig_status = "Kept"

                    signal_counter += 1
                    signal = Signal(
                        signal_id=f"SIG-{signal_counter:03d}",
                        source_name=signal_source,
                        source_url=item["url"],
                        headline=item["headline"],
                        summary=tag_result.get("summary", ""),
                        published_date=_parse_date(
                            tag_result.get("published_date") or item.get("published_date")
                        ),
                        region=_safe_region(tag_result.get("region", "Global")),
                        topic_category=_safe_category(tag_result.get("topic_category", "Other")),
                        raw_content=(item.get("body") or "")[:5000],
                        cycle_id=cycle.cycle_id,
                        is_negative_news=bool(tag_result.get("is_negative_news", False)),
                        mentions_competitor=mentions_comp,
                        is_politically_sensitive=bool(
                            tag_result.get("is_politically_sensitive", False)
                        ),
                        is_opinion=is_opinion,
                        is_pr_article=is_pr,
                        status=sig_status,
                    )
                    signals.append(signal)

                except Exception as e:
                    signal_counter += 1
                    signal = Signal(
                        signal_id=f"SIG-{signal_counter:03d}",
                        source_name=item.get("source_name") or source_name,
                        source_url=item["url"],
                        headline=item["headline"],
                        summary="Tagging failed -- requires manual triage",
                        published_date=_parse_date(item.get("published_date")),
                        region=Region.GLOBAL,
                        topic_category=TopicCategory.OTHER,
                        raw_content=(item.get("body") or "")[:5000],
                        cycle_id=cycle.cycle_id,
                        is_opinion=False,
                        tagging_failed=True,
                    )
                    signals.append(signal)
                    log.warning("tagging_failed", source=source_name, error=str(e))

        except Exception as e:
            errors.append(f"Source fetch failed: {source_name} -- {e}")
            log.error("source_fetch_failed", source=source_name, error=str(e))
            continue

    # Split into kept vs dropped — all go to sheet, only kept go to ranking
    kept = [s for s in signals if s.status == "Kept"]
    dropped = [s for s in signals if s.status != "Kept"]

    log.info("stage1_filtered", total=len(signals), kept=len(kept),
             dropped=len(dropped),
             dropped_pr=sum(1 for s in dropped if "PR" in s.status),
             dropped_opinion=sum(1 for s in dropped if "Opinion" in s.status),
             dropped_irrelevant=sum(1 for s in dropped if "Irrelevant" in s.status))

    # Deduplicate only the kept signals
    before_dedup = len(kept)
    kept = _deduplicate_signals(kept)
    log.info("stage1_dedup", before=before_dedup, after=len(kept),
             merged=before_dedup - len(kept))

    log.info("stage1_complete", signal_count=len(kept), error_count=len(errors))

    # Return ALL signals (for sheet writing) but only kept ones go forward
    updated_cycle = cycle.model_copy(update={"signal_count": len(kept), "stage": 2})
    return {
        "signals": kept,          # Only kept signals go to ranking
        "all_signals": signals,   # All signals (incl dropped) for sheet
        "errors": errors,
        "cycle": updated_cycle,
    }


# -- Helper functions --


async def _fetch_source(source: dict) -> list[dict]:
    """Fetch content items from a source.

    Dispatches based on fields present in the source config:
      - rss_url        → direct RSS fetch
      - search_queries → Google News discovery
      - neither        → returns [] (source not yet fetchable)
    """
    from src.scrapers import fetch_source_items
    return fetch_source_items(source)


def _is_duplicate(url: str, cycle_id: str) -> bool:
    """Check if this URL has been captured in any previous cycle.

    Returns False on any error (missing DB, schema mismatch, etc.) so ingestion
    degrades gracefully when the DB is not yet initialised.
    """
    try:
        from src.models.database import SessionLocal, SignalRow
        with SessionLocal() as db:
            existing = db.query(SignalRow).filter(SignalRow.source_url == url).first()
            return existing is not None
    except Exception:
        return False


def _passes_recency_check(item: dict, source: dict) -> bool:
    """Apply recency rules: news < 30 days, reports/data < 12 months."""
    pub_date = item.get("published_date")
    if not pub_date:
        return True  # If no date, let it through (Claude will tag it)

    if isinstance(pub_date, str):
        try:
            pub_date = datetime.fromisoformat(pub_date)
        except (ValueError, TypeError):
            return True

    now = datetime.now(timezone.utc)
    if pub_date.tzinfo is None:
        pub_date = pub_date.replace(tzinfo=timezone.utc)

    source_type = source.get("type", "news")
    if source_type in ("report", "data"):
        max_age = timedelta(days=365)
    else:
        max_age = timedelta(days=30)

    return (now - pub_date) <= max_age


async def _tag_with_llm(
    source_name: str,
    url: str,
    headline: str,
    body: str,
) -> dict:
    """Call the configured LLM to extract structured tags from a content item."""
    from src.llm import complete_json

    prompt = TAGGING_PROMPT.format(
        source_name=source_name, url=url, headline=headline, body=body[:3000]
    )

    return await complete_json(
        role="generation",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
    )


def _parse_date(date_val) -> datetime | None:
    """Parse ISO date string (or passthrough datetime), return None if unparseable."""
    if not date_val:
        return None
    if isinstance(date_val, datetime):
        return date_val
    try:
        return datetime.fromisoformat(str(date_val).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


_REGION_ALIASES = {
    "uk": Region.UK, "united kingdom": Region.UK, "britain": Region.UK, "gb": Region.UK,
    "usa": Region.USA, "us": Region.USA, "united states": Region.USA, "america": Region.USA,
    "australia": Region.AUSTRALIA, "au": Region.AUSTRALIA,
    "canada": Region.CANADA, "ca": Region.CANADA,
    "europe": Region.EUROPE, "eu": Region.EUROPE,
    "global": Region.GLOBAL, "international": Region.GLOBAL,
}

_CATEGORY_ALIASES = {
    "rent": TopicCategory.RENT_TRENDS, "rent trends": TopicCategory.RENT_TRENDS,
    "visa": TopicCategory.VISA_DATA, "visa data": TopicCategory.VISA_DATA,
    "student demand": TopicCategory.STUDENT_DEMAND, "demand": TopicCategory.STUDENT_DEMAND,
    "policy": TopicCategory.POLICY_CHANGES, "policy changes": TopicCategory.POLICY_CHANGES,
    "supply": TopicCategory.SUPPLY_OUTLOOK, "supply outlook": TopicCategory.SUPPLY_OUTLOOK,
    "emerging markets": TopicCategory.EMERGING_MARKETS,
    "rankings": TopicCategory.QS_RANKINGS, "qs rankings": TopicCategory.QS_RANKINGS,
    "other": TopicCategory.OTHER,
}


def _safe_region(value) -> Region:
    if isinstance(value, Region):
        return value
    return _REGION_ALIASES.get(str(value or "").strip().lower(), Region.GLOBAL)


def _safe_category(value) -> TopicCategory:
    if isinstance(value, TopicCategory):
        return value
    return _CATEGORY_ALIASES.get(str(value or "").strip().lower(), TopicCategory.OTHER)


def _deduplicate_signals(signals: list) -> list:
    """Merge signals about the same news from different sources.

    Groups by headline similarity (word overlap), keeps the best summary
    (longest / most data points), and merges source URLs into one signal.
    The source_name becomes "Source1, Source2, ..." and source_url contains
    all URLs separated by newlines.
    """
    import re

    if not signals:
        return signals

    def _headline_words(headline: str) -> set[str]:
        """Extract significant words from headline for comparison."""
        stop = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "is", "are",
                "by", "with", "from", "as", "its", "it", "this", "that", "has", "have", "be"}
        words = set(re.sub(r'[^\w\s]', '', headline.lower()).split())
        return words - stop

    def _data_point_count(summary: str) -> int:
        """Count numeric data points in a summary."""
        return len(re.findall(r'\d+[%.]?\d*', summary))

    # Group signals by headline similarity
    groups: list[list] = []
    used: set[int] = set()

    for i, sig_a in enumerate(signals):
        if i in used:
            continue
        group = [sig_a]
        used.add(i)
        words_a = _headline_words(sig_a.headline)

        if len(words_a) < 2:
            groups.append(group)
            continue

        for j, sig_b in enumerate(signals):
            if j in used:
                continue
            words_b = _headline_words(sig_b.headline)
            if len(words_b) < 2:
                continue

            # Calculate word overlap ratio
            overlap = len(words_a & words_b)
            min_len = min(len(words_a), len(words_b))
            if min_len > 0 and overlap / min_len >= 0.5:
                # Same region check — only merge if same region or one is Global
                if (sig_a.region == sig_b.region or
                    sig_a.region == Region.GLOBAL or sig_b.region == Region.GLOBAL):
                    group.append(sig_b)
                    used.add(j)

        groups.append(group)

    # Merge each group into one signal
    merged: list = []
    for group in groups:
        if len(group) == 1:
            merged.append(group[0])
            continue

        # Pick the best summary (most data points, then longest)
        best = max(group, key=lambda s: (_data_point_count(s.summary), len(s.summary)))

        # Merge source names and URLs
        source_names = list(dict.fromkeys(s.source_name for s in group))
        source_urls = list(dict.fromkeys(s.source_url for s in group if s.source_url))

        # Use the best signal as base, update source info
        best.source_name = ", ".join(source_names[:5])
        best.source_url = "\n".join(source_urls[:5])

        # Use the most specific region (not Global) if available
        non_global = [s for s in group if s.region != Region.GLOBAL]
        if non_global:
            best.region = non_global[0].region

        merged.append(best)

    # Re-number signal IDs
    for i, sig in enumerate(merged, 1):
        sig.signal_id = f"SIG-{i:03d}"

    return merged
