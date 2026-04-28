"""Firecrawl client — optional full-article scraping.

For Phase 1 V1 we don't scrape individual articles (snippets from Google News
and direct RSS feeds give the LLM enough to tag and rank).  This stub is
in place so Phase 2 can enrich signals with full article bodies.
"""

from __future__ import annotations

import structlog

from src.settings import settings

log = structlog.get_logger()


async def scrape_url(url: str) -> dict | None:
    """Scrape a single URL via Firecrawl.  Returns {headline, body} or None."""
    if not settings.firecrawl_api_key:
        return None

    try:
        from firecrawl import FirecrawlApp  # type: ignore
    except ImportError:
        log.warning("firecrawl_not_installed")
        return None

    try:
        app = FirecrawlApp(api_key=settings.firecrawl_api_key)
        result = app.scrape_url(url)
        if not result:
            return None
        data = result if isinstance(result, dict) else getattr(result, "__dict__", {})
        metadata = data.get("metadata", {}) or {}
        return {
            "headline": metadata.get("title", "") or metadata.get("ogTitle", ""),
            "body": (data.get("markdown") or data.get("content") or "")[:5000],
        }
    except Exception as e:
        log.error("firecrawl_failed", url=url, error=str(e))
        return None
