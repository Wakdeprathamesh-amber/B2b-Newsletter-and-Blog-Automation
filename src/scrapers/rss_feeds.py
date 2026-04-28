"""Generic RSS feed fetcher — for sources that expose a direct feed.

Used by sources in config/sources.json that have an `rss_url` field set.
"""

from __future__ import annotations

import re
from datetime import datetime

import feedparser
import structlog

log = structlog.get_logger()


def fetch_rss(feed_url: str, limit: int = 20, source_name: str = "") -> list[dict]:
    """Fetch a direct RSS/Atom feed.

    Returns list of dicts: url, headline, body, published_date, source_name.
    Returns an empty list on any parse error — never raises.
    """
    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        log.error("rss_fetch_failed", url=feed_url, error=str(e))
        return []

    if not feed.entries:
        log.warning("rss_no_entries", url=feed_url, bozo=getattr(feed, "bozo", False))
        return []

    results: list[dict] = []
    for entry in feed.entries[:limit]:
        published = _parse_published(entry)
        body = _strip_html(entry.get("summary", "") or entry.get("description", ""))

        results.append(
            {
                "url": entry.get("link", ""),
                "headline": entry.get("title", "").strip(),
                "body": body,
                "published_date": published,
                "source_name": source_name or feed.feed.get("title", "RSS"),
            }
        )

    log.info("rss_fetch_ok", url=feed_url, found=len(results))
    return results


def _parse_published(entry) -> datetime | None:
    if entry.get("published_parsed"):
        try:
            return datetime(*entry.published_parsed[:6])
        except Exception:
            pass
    if entry.get("updated_parsed"):
        try:
            return datetime(*entry.updated_parsed[:6])
        except Exception:
            pass
    return None


_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def _strip_html(text: str) -> str:
    text = _TAG_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()
