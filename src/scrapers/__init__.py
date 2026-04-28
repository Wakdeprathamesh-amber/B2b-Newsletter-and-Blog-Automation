"""Scraper orchestrator.

Dispatches each source in config/sources.json to the right fetcher:
  - source.rss_url        → rss_feeds.fetch_rss
  - source.search_queries → google_news.search (per query)
  - otherwise             → skipped (not yet implemented)

Date filtering: Only returns items within the current Amber Beat week
window (e.g. 22nd-28th for Week 4).
"""

from __future__ import annotations

import re

import structlog

from src.scrapers.date_window import get_google_news_date_param, is_within_window
from src.scrapers.google_news import search as google_news_search
from src.scrapers.rss_feeds import fetch_rss

log = structlog.get_logger()


def fetch_source_items(source: dict) -> list[dict]:
    """Fetch all items for a single source config entry.

    Each item is a dict: {url, headline, body, published_date, source_name}.
    Items are de-duped by URL and filtered to the current week window.
    """
    items: list[dict] = []

    # 1. Direct RSS feed
    rss_url = source.get("rss_url")
    if rss_url:
        items.extend(fetch_rss(rss_url, limit=source.get("limit", 20), source_name=source["name"]))

    # 2. Google News discovery queries — replace 'when:14d' with precise date range
    queries = source.get("search_queries", [])
    per_query = source.get("limit_per_query", 6)
    hl = source.get("hl", "en-GB")
    gl = source.get("gl", "GB")
    date_param = get_google_news_date_param()

    for q in queries:
        # Skip section markers like "__UK__"
        if q.startswith("__") and q.endswith("__"):
            continue
        # Replace 'when:14d' or 'when:7d' with precise date window
        clean_query = re.sub(r"when:\d+d", date_param, q)
        items.extend(google_news_search(clean_query, limit=per_query, hl=hl, gl=gl))

    # Dedupe within this source by URL
    seen: set[str] = set()
    unique: list[dict] = []
    for item in items:
        url = item.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)

        # Filter by date window (only keep items from current Amber Beat week)
        if not is_within_window(item.get("published_date")):
            continue

        unique.append(item)

    return unique
