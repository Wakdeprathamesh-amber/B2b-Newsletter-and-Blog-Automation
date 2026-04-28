"""Google Sheets writer — pushes pipeline output into the master sheet.

Tabs expected (created by setup_sheet.py):
  Dashboard, Cycles, Signals, Ranked Topics,
  LinkedIn Drafts, Blog Drafts, Newsletter, Newsroom Blog, Publishing Log,
  Feedback, Errors, Reference
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

import gspread
import structlog
from google.oauth2.service_account import Credentials

from src.settings import settings

log = structlog.get_logger()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CHUNK_SIZE = 25


class SheetsClient:
    """Thin wrapper around gspread for pipeline writes.

    All writes are append-only except `update_dashboard` and `update_cycle_row`
    which patch existing rows.
    """

    def __init__(self) -> None:
        if not settings.google_service_account_json:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not set in .env")
        if not settings.google_master_sheet_id:
            raise RuntimeError("GOOGLE_MASTER_SHEET_ID not set in .env")

        creds = Credentials.from_service_account_file(
            settings.google_service_account_json, scopes=SCOPES
        )
        self._gc = gspread.authorize(creds)
        self._sheet = self._gc.open_by_key(settings.google_master_sheet_id)
        self._ws_cache: dict[str, gspread.Worksheet] = {}
        log.info("sheets_connected", title=self._sheet.title)

    def _ws(self, name: str) -> gspread.Worksheet:
        if name not in self._ws_cache:
            self._ws_cache[name] = self._sheet.worksheet(name)
        return self._ws_cache[name]

    def _reconnect(self) -> None:
        """Re-authenticate and reopen the sheet (resets stale connections)."""
        creds = Credentials.from_service_account_file(
            settings.google_service_account_json, scopes=SCOPES
        )
        self._gc = gspread.authorize(creds)
        self._sheet = self._gc.open_by_key(settings.google_master_sheet_id)
        self._ws_cache.clear()

    def _append(self, tab: str, rows: list[list[Any]]) -> int:
        """Append rows in chunks to avoid timeouts on large batches."""
        if not rows:
            return 0

        total = 0
        for i in range(0, len(rows), CHUNK_SIZE):
            chunk = rows[i : i + CHUNK_SIZE]
            try:
                ws = self._ws(tab)
                ws.append_rows(chunk, value_input_option="USER_ENTERED")
                total += len(chunk)
            except Exception:
                self._reconnect()
                ws = self._ws(tab)
                ws.append_rows(chunk, value_input_option="USER_ENTERED")
                total += len(chunk)

        log.info("sheets_append", tab=tab, count=total)
        return total

    # ── Stage 1: Signals (sorted by region: UK → USA → AU → EU → Global) ─
    def append_signals(self, signals: Iterable, cycle_date: str = "") -> int:
        # Sort signals by region order for better sheet UX
        region_order = {"UK": 0, "USA": 1, "Australia": 2, "Canada": 3, "Europe": 4, "Global": 5}
        sorted_signals = sorted(
            signals,
            key=lambda s: region_order.get(_val(s.region), 6),
        )
        rows: list[list[Any]] = []
        for s in sorted_signals:
            rows.append(
                [
                    s.signal_id or "",
                    cycle_date or _human_date(s.captured_at),
                    _iso(s.captured_at),
                    s.source_name,
                    s.source_url,
                    s.headline,
                    s.summary,
                    _human_date(s.published_date) if s.published_date else "",
                    _val(s.region),
                    _val(s.topic_category),
                    _yn(s.is_negative_news),
                    _yn(s.mentions_competitor),
                    _yn(s.is_politically_sensitive),
                    _yn(getattr(s, "is_opinion", False)),
                    _yn(s.tagging_failed),
                    getattr(s, "status", "Kept"),
                    (s.raw_content or "")[:500],
                ]
            )
        return self._append("Signals", rows)

    # ── Ranked Topics (sorted by region then rank) ─────────────────────
    # New columns: decision, channels, linkedin_voice, blog_lens,
    # edited_title, edited_summary, content_guidance, reviewer_notes
    def append_ranked_topics(self, topics: Iterable, cycle_date: str = "") -> int:
        region_order = {"UK": 0, "USA": 1, "Australia": 2, "Canada": 3, "Europe": 4, "Global": 5}
        sorted_topics = sorted(
            topics,
            key=lambda t: (region_order.get(_val(t.primary_region), 6), t.rank),
        )
        rows: list[list[Any]] = []
        for t in sorted_topics:
            ref_links = _format_references(t.source_urls if hasattr(t, "source_urls") else [])
            rows.append(
                [
                    t.topic_id or "",
                    cycle_date or "",
                    t.rank,
                    t.title,
                    t.summary,
                    _val(t.urgency),
                    _val(t.primary_region),
                    ", ".join(_val(a) for a in (t.stakeholder_tags or [])),
                    ref_links,
                    "Pending",   # decision — human sets to Approve/Reject
                    "",          # channels — human selects: Newsroom, LinkedIn, Blog, Newsletter
                    "",          # linkedin_voice — human picks if LinkedIn selected
                    "",          # blog_lens — human picks if Blog selected
                    "",          # edited_title
                    "",          # edited_summary
                    t.content_guidance or "",  # content_guidance — AI-generated editorial direction
                    "",          # reviewer_notes — human adds notes
                ]
            )
        return self._append("Ranked Topics", rows)

    # ── Stage 4D: Newsroom Blog Items ───────────────────────────────
    def append_newsroom_items(
        self,
        newsroom_items: dict,
        cycle_id: str = "",
        cycle_date: str = "",
        topic_titles: dict[str, str] | None = None,
    ) -> int:
        """Write newsroom blog items (dict keyed by region) to the Newsroom Blog tab."""
        rows: list[list[Any]] = []
        topic_titles = topic_titles or {}
        region_order = ["UK", "USA", "Australia", "Canada", "Europe", "Global"]
        for region in region_order:
            items = newsroom_items.get(region, [])
            for rank, item in enumerate(items, 1):
                topic_id = item.get("topic_id", "")
                rows.append([
                    cycle_id,
                    cycle_date,
                    region,
                    rank,
                    item.get("item_text", ""),
                    item.get("word_count", len(item.get("item_text", "").split())),
                    _yn(item.get("valid", True)),
                    topic_id,
                    topic_titles.get(topic_id, ""),
                    item.get("source_url", ""),
                    "",  # topic_category
                    "Pending",
                    "",  # reviewer_notes
                    "",  # reviewed_by
                    "",  # reviewed_at
                ])
        return self._append("Newsroom Blog", rows)

    # ── Stage 4A: LinkedIn Drafts ────────────────────────────────────
    def append_linkedin_drafts(self, drafts: Iterable, topic_titles: dict[str, str] | None = None) -> int:
        rows: list[list[Any]] = []
        topic_titles = topic_titles or {}
        for d in drafts:
            rows.append(
                [
                    d.draft_id or "",
                    d.cycle_id or "",
                    d.topic_id or "",
                    topic_titles.get(d.topic_id, ""),
                    _val(d.voice),
                    _val(getattr(d, "audience", None) or ""),
                    d.content_body,
                    d.word_count,
                    ", ".join(d.validation_flags) if d.validation_flags else "",
                    _val(d.status),
                    "Pending",  # decision
                    "",  # review_comments
                    "",  # reviewed_by
                    "",  # reviewed_at
                    d.revision_count,
                    "",  # final_content
                    "",  # scheduled_for
                    "",  # publish_url
                ]
            )
        return self._append("LinkedIn Drafts", rows)

    # ── Stage 4C: Newsletter ─────────────────────────────────────────
    def append_newsletter(self, draft, cycle_theme: str = "") -> int:
        row = [
            draft.draft_id or "",
            draft.cycle_id or "",
            cycle_theme,
            draft.content_body,
            "",  # uk_section (full content is in full_content)
            "",  # usa_section
            "",  # australia_section
            "",  # canada_section
            "",  # europe_section
            "",  # quick_stats
            draft.word_count,
            ", ".join(draft.validation_flags) if draft.validation_flags else "",
            _val(draft.status),
            "Pending",  # decision
            "",  # review_comments
            "",  # reviewed_by
            "",  # reviewed_at
            draft.revision_count,
        ]
        return self._append("Newsletter", [row])

    # ── Cycles tab ────────────────────────────────────────────────────
    def append_cycle(self, cycle, counts: dict | None = None) -> int:
        c = counts or {}
        row = [
            cycle.cycle_id,
            _iso(cycle.started_at),
            _iso(cycle.completed_at),
            cycle.stage,
            _val(cycle.status),
            c.get("signals", cycle.signal_count),
            c.get("ranked", 0),
            c.get("shortlisted", cycle.topic_count),
            c.get("linkedin", 0),
            c.get("blog", 0),
            c.get("newsletter", 0),
            c.get("approved", 0),
            c.get("published", 0),
            len(cycle.error_log),
            "",
        ]
        return self._append("Cycles", [row])

    # ── Dashboard ─────────────────────────────────────────────────────
    def update_dashboard(self, **metrics: Any) -> None:
        ws = self._ws("Dashboard")
        mapping = {
            "Active Cycle ID": metrics.get("cycle_id", ""),
            "Current Stage": metrics.get("stage", ""),
            "Status": metrics.get("status", ""),
            "Started At": metrics.get("started_at", ""),
            "Signals Captured": metrics.get("signals", ""),
            "Topics Ranked": metrics.get("ranked", ""),
            "Topics Shortlisted": metrics.get("shortlisted", ""),
            "LinkedIn Drafts": metrics.get("linkedin", ""),
            "Blog Drafts": metrics.get("blog", ""),
            "Newsletter Drafts": metrics.get("newsletter", ""),
            "Drafts Approved": metrics.get("approved", ""),
            "Drafts Published": metrics.get("published", ""),
            "Last Error": metrics.get("last_error", ""),
            "Last Updated": datetime.utcnow().strftime("%-d %b %Y %H:%M UTC"),
        }

        try:
            rows = ws.get_all_values()
        except Exception:
            self._reconnect()
            rows = self._ws("Dashboard").get_all_values()

        updates: list[dict] = []
        for i, row in enumerate(rows, start=1):
            if not row:
                continue
            label = row[0]
            if label in mapping and mapping[label] != "":
                updates.append({"range": f"B{i}", "values": [[str(mapping[label])]]})
        if updates:
            self._ws("Dashboard").batch_update(updates, value_input_option="USER_ENTERED")
            log.info("dashboard_updated", fields=len(updates))

    # ── Errors tab ────────────────────────────────────────────────────
    def append_errors(self, cycle_id: str, stage: str, messages: list[str]) -> int:
        rows: list[list[Any]] = []
        ts = datetime.utcnow().strftime("%-d %b %Y %H:%M")
        for msg in messages:
            rows.append([ts, cycle_id, stage, "error", msg, ""])
        return self._append("Errors", rows)

    # ── Cycle Rotation: archive current data then clear active tabs ────
    def archive_and_clear(self, cycle_id: str, cycle_date: str) -> dict:
        """Archive current active tab data to Archive tabs, then clear active tabs.

        Called at the start of each new cycle. Returns counts of archived rows.

        Flow:
          1. Read rows from each active tab
          2. Prepend cycle_id + cycle_date to each row
          3. Append to corresponding Archive tab
          4. Clear the active tab (keep headers)
        """
        archive_map = {
            "Signals": "Archive - Signals",
            "Ranked Topics": "Archive - Ranked Topics",
            "Newsroom Blog": "Archive - Newsroom Blog",
        }
        # Active tabs that get cleared but NOT archived (content is cycle-specific)
        clear_only = ["LinkedIn Drafts", "Blog Drafts", "Newsletter"]

        counts: dict[str, int] = {}

        for active_tab, archive_tab in archive_map.items():
            try:
                ws = self._ws(active_tab)
                data = ws.get_all_values()
                if len(data) <= 1:
                    counts[active_tab] = 0
                    continue

                headers = data[0]
                rows = data[1:]

                # Build archive rows: cycle_id + cycle_date + selected columns
                archive_rows = self._build_archive_rows(
                    active_tab, headers, rows, cycle_id, cycle_date
                )

                if archive_rows:
                    self._append(archive_tab, archive_rows)

                # Clear active tab
                end_col = chr(64 + len(headers))
                ws.batch_clear([f"A2:{end_col}{len(data)}"])

                counts[active_tab] = len(rows)
                log.info("archived_tab", tab=active_tab, rows=len(rows))

            except Exception as e:
                log.warning("archive_failed", tab=active_tab, error=str(e))
                counts[active_tab] = -1

        # Clear-only tabs (no archiving — content drafts are regenerated each cycle)
        for tab_name in clear_only:
            try:
                ws = self._ws(tab_name)
                data = ws.get_all_values()
                if len(data) > 1:
                    end_col = chr(64 + len(data[0]))
                    ws.batch_clear([f"A2:{end_col}{len(data)}"])
                    counts[tab_name] = len(data) - 1
                else:
                    counts[tab_name] = 0
            except Exception as e:
                log.warning("clear_failed", tab=tab_name, error=str(e))

        return counts

    def _build_archive_rows(
        self, tab_name: str, headers: list, rows: list,
        cycle_id: str, cycle_date: str,
    ) -> list[list]:
        """Build archive rows from active tab data.

        Each archive tab has cycle_id + cycle_date as first two columns,
        then a subset of the active tab's columns.
        """
        col = {h: i for i, h in enumerate(headers)}

        def g(row, name):
            idx = col.get(name)
            if idx is None or idx >= len(row):
                return ""
            return row[idx]

        archive_rows = []

        if tab_name == "Signals":
            for row in rows:
                archive_rows.append([
                    cycle_id, cycle_date,
                    g(row, "signal_id"), g(row, "source_name"), g(row, "source_url"),
                    g(row, "headline"), g(row, "summary"), g(row, "region"),
                    g(row, "topic_category"), g(row, "is_negative_news"),
                    g(row, "is_opinion"), g(row, "status"),
                ])

        elif tab_name == "Ranked Topics":
            for row in rows:
                archive_rows.append([
                    cycle_id, cycle_date,
                    g(row, "topic_id"), g(row, "rank"), g(row, "title"),
                    g(row, "summary"), g(row, "urgency"), g(row, "primary_region"),
                    g(row, "stakeholder_tags"), g(row, "decision"),
                    g(row, "source_references"),
                ])

        elif tab_name == "Newsroom Blog":
            for row in rows:
                archive_rows.append([
                    cycle_id, cycle_date,
                    g(row, "region"), g(row, "item_rank"), g(row, "item_text"),
                    g(row, "word_count"), g(row, "topic_title"),
                    g(row, "source_url"), g(row, "decision"),
                ])

        return archive_rows

    # ── Utility: clear all data rows (keeps headers) ──────────────────
    def clear_all_data(self) -> None:
        tabs_to_clear = [
            "Dashboard", "Cycles", "Signals", "Ranked Topics",
            "LinkedIn Drafts", "Blog Drafts", "Newsletter", "Newsroom Blog",
            "Publishing Log", "Feedback", "Errors",
        ]
        for tab_name in tabs_to_clear:
            try:
                ws = self._ws(tab_name)
                if tab_name == "Dashboard":
                    # Only clear value column (B), keep metric labels (A)
                    rows = ws.get_all_values()
                    updates = []
                    for i in range(2, len(rows) + 1):  # skip header
                        updates.append({"range": f"B{i}", "values": [[""]]})
                    if updates:
                        ws.batch_update(updates, value_input_option="USER_ENTERED")
                else:
                    row_count = ws.row_count
                    if row_count > 1:
                        ws.delete_rows(2, row_count)
                log.info("tab_cleared", tab=tab_name)
            except Exception as e:
                log.warning("tab_clear_failed", tab=tab_name, error=str(e))


# ── Helpers ───────────────────────────────────────────────────────────────
def _iso(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    return str(value)


def _human_date(value: Any) -> str:
    """Format datetime as '11 Apr 2026' for human readability."""
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except Exception:
            return value
    if isinstance(value, datetime):
        return value.strftime("%-d %b %Y")
    return str(value)


def _val(enum_or_str: Any) -> str:
    if enum_or_str is None:
        return ""
    return getattr(enum_or_str, "value", str(enum_or_str))


def _yn(flag: Any) -> str:
    return "Yes" if flag else "No"


def _format_references(urls: list[str]) -> str:
    """Format source URLs as a newline-separated list for readable cells."""
    if not urls:
        return ""
    unique = list(dict.fromkeys(urls))  # dedupe preserving order
    return "\n".join(unique[:8])  # cap at 8 to keep cells manageable
