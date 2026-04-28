"""Google News RSS search — the discovery layer.

Finds fresh articles matching a query, via Google's public RSS endpoint.
No API key required.  Results are ranked by Google News relevance + recency.

Example:
    items = search("international student accommodation UK", limit=8)
    # [{"url": ..., "headline": ..., "body": ..., "published_date": ...}, ...]
"""

from __future__ import annotations

import re
import urllib.parse
from datetime import datetime

import feedparser
import structlog

log = structlog.get_logger()

BASE_URL = "https://news.google.com/rss/search"


def search(
    query: str,
    limit: int = 10,
    hl: str = "en-GB",
    gl: str = "GB",
) -> list[dict]:
    """Search Google News via RSS.

    Args:
        query: Natural-language search query.
        limit: Max results to return.
        hl: UI language ("en-GB", "en-US", etc.).
        gl: Country of interest.

    Returns:
        List of dicts with keys: url, headline, body, published_date, source_name.
    """
    params = {"q": query, "hl": hl, "gl": gl, "ceid": f"{gl}:en"}
    feed_url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"

    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        log.error("google_news_fetch_failed", query=query, error=str(e))
        return []

    if not feed.entries:
        log.warning("google_news_no_results", query=query)
        return []

    results: list[dict] = []
    for entry in feed.entries[:limit]:
        published = _parse_published(entry)
        body = _strip_html(entry.get("summary", ""))

        # Google News embeds the real publisher in either entry.source.title
        # or at the end of the headline: "Headline - Publisher"
        publisher = ""
        if hasattr(entry, "source"):
            src = getattr(entry, "source", None)
            if isinstance(src, dict):
                publisher = src.get("title", "")
            else:
                publisher = getattr(src, "title", "") or str(src)
        if not publisher and " - " in entry.get("title", ""):
            publisher = entry["title"].rsplit(" - ", 1)[-1]

        headline = entry.get("title", "")
        if publisher and headline.endswith(f" - {publisher}"):
            headline = headline[: -(len(publisher) + 3)]

        results.append(
            {
                "url": entry.get("link", ""),
                "headline": headline.strip(),
                "body": body,
                "published_date": published,
                "source_name": publisher or "Google News",
            }
        )

    log.info("google_news_search", query=query, found=len(results))
    return results


def _parse_published(entry) -> datetime | None:
    if entry.get("published_parsed"):
        try:
            return datetime(*entry.published_parsed[:6])
        except Exception:
            pass
    return None


_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def _strip_html(text: str) -> str:
    text = _TAG_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()
