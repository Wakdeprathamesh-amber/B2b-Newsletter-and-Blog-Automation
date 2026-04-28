"""Initialise the master Google Sheet for the Amber Content Engine.

Idempotent:
  - Creates missing tabs
  - Rewrites the header row on existing tabs (preserving data below)
  - Applies formatting, frozen panes, column widths, and dropdown validation

Run:  python3 setup_sheet.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials


# ── .env loader ────────────────────────────────────────────────────────────
def load_env(path: str = ".env") -> dict:
    env: dict = {}
    if not Path(path).exists():
        return env
    for raw in Path(path).read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


# ── Reusable dropdown option sets ──────────────────────────────────────────
CYCLE_STATUS = [
    "Running", "Ranking", "Review", "Generating", "Complete", "Failed",
]
SIGNAL_STATUS = ["Kept", "Dropped (PR)", "Dropped (Opinion)", "Dropped (Irrelevant)",
                  "Dropped (Competitor)", "Dropped (Duplicate)", "Dropped (Recency)"]
REGIONS = ["UK", "USA", "Australia", "Canada", "Europe", "Global"]
URGENCY = ["Breaking", "Time-sensitive", "Evergreen"]
BOOL_YN = ["Yes", "No"]
TOPIC_CATEGORIES = [
    "Rent Trends", "Visa Data", "Student Demand", "Policy Changes",
    "Supply Outlook", "Emerging Markets", "QS Rankings", "Other",
]
TOPIC_DECISION = ["Pending", "Approve", "Edit", "Reject"]
DRAFT_DECISION = ["Pending", "Approve", "Needs Edit", "Reject"]
DRAFT_STATUS = [
    "Draft", "Under Review", "Approved", "Needs Edit",
    "Rejected", "Revised", "Published", "Failed",
]
LINKEDIN_VOICE = ["", "Amber Brand", "Madhur", "Jools"]
BLOG_LENS = ["", "Supply Partner", "University / HE", "HEA / Agents"]
# Channels: human selects which content types each topic should feed
# Comma-separated in the cell, e.g. "Newsroom, LinkedIn, Blog"
CHANNEL_OPTIONS = ["Newsroom", "LinkedIn", "Blog", "Newsletter",
                   "Newsroom, LinkedIn", "Newsroom, LinkedIn, Blog",
                   "Newsroom, Newsletter", "Newsroom, LinkedIn, Blog, Newsletter"]
SEVERITY = ["info", "warning", "error"]


# ── Tab specs ──────────────────────────────────────────────────────────────
# Each tab: name, headers, column widths (px), dropdowns {col_name: [options]},
# wrap_cols (cells that hold long text), seed_rows (optional static rows)
TABS = [
    {
        "name": "Dashboard",
        "headers": ["Metric", "Value"],
        "widths":  [220, 500],
        "seed_rows": [
            ["Active Cycle ID",         ""],
            ["Current Stage",           ""],
            ["Status",                  ""],
            ["Started At",              ""],
            ["Signals Captured",        ""],
            ["Topics Ranked",           ""],
            ["Topics Shortlisted",      ""],
            ["LinkedIn Drafts",         ""],
            ["Blog Drafts",             ""],
            ["Newsletter Drafts",       ""],
            ["Drafts Approved",         ""],
            ["Drafts Published",        ""],
            ["Last Error",              ""],
            ["Last Updated",            ""],
        ],
    },
    {
        "name": "Cycles",
        "headers": [
            "cycle_id", "started_at", "completed_at", "current_stage", "status",
            "signal_count", "ranked_topic_count", "shortlisted_count",
            "linkedin_count", "blog_count", "newsletter_count",
            "approved_count", "published_count", "error_count", "notes",
        ],
        "widths":  [180, 160, 160, 110, 140, 110, 140, 130, 115, 95, 125, 120, 120, 100, 300],
        "dropdowns": {"status": CYCLE_STATUS},
    },
    {
        "name": "Signals",
        "headers": [
            "signal_id", "cycle_date", "fetched_at", "source_name", "source_url",
            "headline", "summary", "published_date", "region", "topic_category",
            "is_negative_news", "mentions_competitor", "is_politically_sensitive",
            "is_opinion", "tagging_failed", "status", "raw_excerpt",
        ],
        "widths":  [100, 130, 150, 180, 320, 300, 500, 130, 90, 140,
                    120, 140, 160, 100, 120, 170, 400],
        "dropdowns": {
            "region": REGIONS,
            "topic_category": TOPIC_CATEGORIES,
            "is_negative_news": BOOL_YN,
            "mentions_competitor": BOOL_YN,
            "is_politically_sensitive": BOOL_YN,
            "is_opinion": BOOL_YN,
            "tagging_failed": BOOL_YN,
            "status": SIGNAL_STATUS,
        },
        "wrap_cols": ["headline", "summary", "raw_excerpt"],
    },
    {
        "name": "Ranked Topics",
        "headers": [
            "topic_id", "cycle_date", "rank", "title", "summary", "urgency",
            "primary_region", "stakeholder_tags", "source_references",
            "decision", "channels", "linkedin_voice", "blog_lens",
            "edited_title", "edited_summary", "content_guidance", "reviewer_notes",
        ],
        "widths":  [100, 120, 55, 280, 450, 120, 120, 180, 400,
                    110, 200, 130, 160,
                    280, 400, 360, 360],
        "dropdowns": {
            "urgency": URGENCY,
            "primary_region": REGIONS,
            "decision": TOPIC_DECISION,
            "channels": CHANNEL_OPTIONS,
            "linkedin_voice": LINKEDIN_VOICE,
            "blog_lens": BLOG_LENS,
        },
        "wrap_cols": ["title", "summary", "source_references",
                      "edited_title", "edited_summary", "content_guidance", "reviewer_notes"],
    },
    {
        "name": "Newsroom Blog",
        "headers": [
            "cycle_id", "cycle_date", "region", "item_rank", "item_text",
            "word_count", "valid", "topic_id", "topic_title",
            "source_url", "topic_category", "decision",
            "reviewer_notes", "reviewed_by", "reviewed_at",
        ],
        "widths":  [180, 130, 100, 80, 600, 90, 70, 120, 280,
                    350, 140, 120, 360, 140, 160],
        "dropdowns": {
            "region": REGIONS,
            "valid": BOOL_YN,
            "decision": TOPIC_DECISION,
        },
        "wrap_cols": ["item_text", "topic_title", "reviewer_notes"],
    },
    {
        "name": "LinkedIn Drafts",
        "headers": [
            "draft_id", "cycle_id", "topic_id", "topic_title", "voice",
            "region", "content_body", "word_count", "validation_flags",
            "status", "decision", "review_comments", "reviewed_by",
            "reviewed_at", "revision_count", "final_content",
            "scheduled_for", "publish_url",
        ],
        "widths":  [180, 180, 180, 260, 130, 95, 520, 100, 260, 130,
                    130, 360, 140, 160, 110, 520, 160, 280],
        "dropdowns": {
            "voice": LINKEDIN_VOICE,
            "region": REGIONS,
            "status": DRAFT_STATUS,
            "decision": DRAFT_DECISION,
        },
        "wrap_cols": [
            "topic_title", "content_body", "validation_flags",
            "review_comments", "final_content",
        ],
    },
    {
        "name": "Blog Drafts",
        "headers": [
            "draft_id", "cycle_id", "topic_id", "topic_title", "lens",
            "audience", "content_body", "word_count", "validation_flags",
            "status", "decision", "review_comments", "reviewed_by",
            "reviewed_at", "revision_count", "final_content", "publish_url",
        ],
        "widths":  [180, 180, 180, 260, 170, 140, 560, 100, 260, 130,
                    130, 360, 140, 160, 110, 560, 280],
        "dropdowns": {
            "lens": BLOG_LENS,
            "status": DRAFT_STATUS,
            "decision": DRAFT_DECISION,
        },
        "wrap_cols": [
            "topic_title", "content_body", "validation_flags",
            "review_comments", "final_content",
        ],
    },
    {
        "name": "Newsletter",
        "headers": [
            "draft_id", "cycle_id", "cycle_theme", "full_content",
            "uk_section", "usa_section", "australia_section", "canada_section",
            "europe_section",
            "quick_stats", "word_count", "validation_flags", "status",
            "decision", "review_comments", "reviewed_by", "reviewed_at",
            "revision_count",
        ],
        "widths":  [180, 180, 300, 600, 400, 400, 400, 400, 400, 360, 100, 260,
                    130, 130, 360, 140, 160, 110],
        "dropdowns": {
            "status": DRAFT_STATUS,
            "decision": DRAFT_DECISION,
        },
        "wrap_cols": [
            "cycle_theme", "full_content", "uk_section", "usa_section",
            "australia_section", "canada_section", "europe_section", "quick_stats",
            "validation_flags", "review_comments",
        ],
    },
    {
        "name": "Errors",
        "headers": ["timestamp", "cycle_id", "stage", "severity", "message", "traceback"],
        "widths":  [160, 180, 120, 110, 400, 500],
        "dropdowns": {"severity": SEVERITY},
        "wrap_cols": ["message", "traceback"],
    },
    {
        "name": "Reference",
        "headers": ["Category", "Key", "Label", "Description"],
        "widths":  [140, 180, 220, 500],
        "seed_rows": [
            ["Voice", "amber_brand", "Amber Company Page", "Data-led, authoritative, uses 'we'; 150-300 words; 3-5 hashtags"],
            ["Voice", "madhur", "Madhur (Thought Leadership)", "Opinionated, personal POV, uses 'I'; 150-250 words; no hashtags"],
            ["Voice", "jools", "Jools (Thought Leadership)", "HE partnership insider, uses 'I'; 150-250 words; no hashtags"],
            ["Voice", "blog_supply", "Blog — Supply Partner", "Operator language, yield/occupancy focus"],
            ["Voice", "blog_university", "Blog — University / HE", "Policy-aware, strategic, finance-sensitive"],
            ["Voice", "blog_hea", "Blog — HEA / Agents", "Market intelligence, recruitment corridor focus"],
            ["Voice", "newsletter_global", "Newsletter — Global", "3-sentence regional sections, quick-stats strip, <500 words"],
            ["", "", "", ""],
            ["Audience", "supply", "Supply Partners", "Property managers, PBSA operators, asset managers"],
            ["Audience", "university", "Universities / HE", "Housing teams, Dean of Students, International Office"],
            ["Audience", "hea", "HEA / Agents", "Senior counsellors, franchise owners, frontline advisors"],
            ["", "", "", ""],
            ["Region", "UK",        "United Kingdom",   "Primary market"],
            ["Region", "USA",       "United States",    "Secondary market"],
            ["Region", "Australia", "Australia",        "Secondary market"],
            ["Region", "Canada",    "Canada",           "Secondary market"],
            ["Region", "Europe",    "Europe (non-UK)",  "Tertiary market"],
            ["Region", "Global",    "Global / Multi",   "Cross-region items"],
            ["", "", "", ""],
            ["Urgency", "Breaking",        "Breaking",        "Must publish this week"],
            ["Urgency", "Time-sensitive",  "Time-sensitive",  "Publish within 2 weeks"],
            ["Urgency", "Evergreen",       "Evergreen",       "Flexible timing"],
        ],
    },
    # ── Archive tabs (accumulate across cycles, never cleared) ──────────
    {
        "name": "Archive - Signals",
        "headers": [
            "cycle_id", "cycle_date", "signal_id", "source_name", "source_url",
            "headline", "summary", "region", "topic_category",
            "is_negative_news", "is_opinion", "status",
        ],
        "widths": [160, 120, 100, 180, 320, 300, 500, 90, 140, 100, 100, 100],
        "dropdowns": {"region": REGIONS, "is_negative_news": BOOL_YN, "is_opinion": BOOL_YN},
        "wrap_cols": ["headline", "summary"],
    },
    {
        "name": "Archive - Ranked Topics",
        "headers": [
            "cycle_id", "cycle_date", "topic_id", "rank", "title", "summary",
            "urgency", "primary_region", "stakeholder_tags", "total_score",
            "source_references",
        ],
        "widths": [160, 120, 100, 55, 280, 400, 130, 130, 180, 110, 420],
        "dropdowns": {"urgency": URGENCY, "primary_region": REGIONS},
        "wrap_cols": ["title", "summary", "source_references"],
    },
    {
        "name": "Archive - Newsroom Blog",
        "headers": [
            "cycle_id", "cycle_date", "region", "item_rank", "item_text",
            "word_count", "topic_title", "source_url", "decision",
        ],
        "widths": [160, 120, 100, 80, 600, 90, 280, 350, 120],
        "dropdowns": {"region": REGIONS, "decision": TOPIC_DECISION},
        "wrap_cols": ["item_text", "topic_title"],
    },
]


# ── Formatting helpers ─────────────────────────────────────────────────────
HEADER_BG = {"red": 0.12, "green": 0.22, "blue": 0.35}
HEADER_FG = {"red": 1.0, "green": 1.0, "blue": 1.0}


def header_format_request(sheet_id: int, col_count: int) -> dict:
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0, "endRowIndex": 1,
                "startColumnIndex": 0, "endColumnIndex": col_count,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": HEADER_BG,
                    "textFormat": {"foregroundColor": HEADER_FG, "bold": True, "fontSize": 11},
                    "horizontalAlignment": "LEFT",
                    "verticalAlignment": "MIDDLE",
                    "wrapStrategy": "CLIP",
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)",
        }
    }


def freeze_row_request(sheet_id: int) -> dict:
    return {
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {"frozenRowCount": 1},
            },
            "fields": "gridProperties.frozenRowCount",
        }
    }


def column_width_request(sheet_id: int, col_index: int, width: int) -> dict:
    return {
        "updateDimensionProperties": {
            "range": {
                "sheetId": sheet_id, "dimension": "COLUMNS",
                "startIndex": col_index, "endIndex": col_index + 1,
            },
            "properties": {"pixelSize": width},
            "fields": "pixelSize",
        }
    }


def wrap_column_request(sheet_id: int, col_index: int) -> dict:
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1, "endRowIndex": 2000,
                "startColumnIndex": col_index, "endColumnIndex": col_index + 1,
            },
            "cell": {
                "userEnteredFormat": {
                    "wrapStrategy": "WRAP",
                    "verticalAlignment": "TOP",
                }
            },
            "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)",
        }
    }


def dropdown_request(sheet_id: int, col_index: int, options: list[str]) -> dict:
    return {
        "setDataValidation": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1, "endRowIndex": 2000,
                "startColumnIndex": col_index, "endColumnIndex": col_index + 1,
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_LIST",
                    "values": [{"userEnteredValue": v} for v in options],
                },
                "showCustomUi": True,
                "strict": False,
            },
        }
    }


def banding_request(sheet_id: int, col_count: int) -> dict:
    """Alternating row colors for readability."""
    return {
        "addBanding": {
            "bandedRange": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "startColumnIndex": 0, "endColumnIndex": col_count,
                },
                "rowProperties": {
                    "headerColor": HEADER_BG,
                    "firstBandColor":  {"red": 1.0,  "green": 1.0,  "blue": 1.0},
                    "secondBandColor": {"red": 0.96, "green": 0.97, "blue": 0.98},
                },
            }
        }
    }


# ── Main logic ─────────────────────────────────────────────────────────────
def ensure_worksheet(sheet: gspread.Spreadsheet, name: str, cols: int) -> gspread.Worksheet:
    try:
        ws = sheet.worksheet(name)
        # Ensure enough columns
        if ws.col_count < cols:
            ws.add_cols(cols - ws.col_count)
        return ws
    except gspread.exceptions.WorksheetNotFound:
        return sheet.add_worksheet(title=name, rows=500, cols=max(cols, 26))


def setup_tab(sheet: gspread.Spreadsheet, spec: dict) -> list[dict]:
    name = spec["name"]
    headers = spec["headers"]
    widths = spec.get("widths", [])
    dropdowns = spec.get("dropdowns", {})
    wrap_cols = spec.get("wrap_cols", [])
    seed_rows = spec.get("seed_rows", [])

    ws = ensure_worksheet(sheet, name, len(headers))
    sheet_id = ws.id

    # Write headers (and optional seed rows)
    ws.update(
        range_name="A1",
        values=[headers] + seed_rows if seed_rows else [headers],
    )

    requests: list[dict] = [
        freeze_row_request(sheet_id),
        header_format_request(sheet_id, len(headers)),
    ]

    # Only add banding on a fresh tab (addBanding errors on duplicate).
    # We swallow the error quietly via try/except in apply_batch.
    requests.append(banding_request(sheet_id, len(headers)))

    for i, w in enumerate(widths):
        requests.append(column_width_request(sheet_id, i, w))

    for col_name in wrap_cols:
        if col_name in headers:
            requests.append(wrap_column_request(sheet_id, headers.index(col_name)))

    for col_name, options in dropdowns.items():
        if col_name in headers:
            requests.append(dropdown_request(sheet_id, headers.index(col_name), options))

    return requests


def apply_batch(sheet: gspread.Spreadsheet, requests: list[dict]) -> None:
    """Apply batch requests, retrying one-at-a-time if any fail (e.g. duplicate banding)."""
    try:
        sheet.batch_update({"requests": requests})
    except Exception:
        for req in requests:
            try:
                sheet.batch_update({"requests": [req]})
            except Exception as e:
                kind = next(iter(req))
                print(f"    skipped {kind}: {e}")


def main() -> int:
    env = load_env()
    cred_path = env.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    sheet_id = env.get("GOOGLE_MASTER_SHEET_ID", "")
    if not cred_path or not sheet_id:
        print("Missing GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_MASTER_SHEET_ID in .env")
        return 1

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(cred_path, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id)

    print(f"\nConnected to: {sheet.title!r}")
    print(f"Existing tabs: {[w.title for w in sheet.worksheets()]}\n")

    for spec in TABS:
        print(f"  Setting up: {spec['name']}")
        requests = setup_tab(sheet, spec)
        apply_batch(sheet, requests)

    # Optional: delete the default "Sheet1" if it's still empty
    try:
        default = sheet.worksheet("Sheet1")
        values = default.get_all_values()
        if not values or (len(values) <= 1 and all(not c for row in values for c in row)):
            sheet.del_worksheet(default)
            print("\n  Removed empty default 'Sheet1'")
    except gspread.exceptions.WorksheetNotFound:
        pass

    print("\nDone.  Open the sheet to review:")
    print(f"  https://docs.google.com/spreadsheets/d/{sheet_id}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
