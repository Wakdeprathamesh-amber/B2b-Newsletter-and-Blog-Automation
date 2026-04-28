"""Calculate the Amber Beat weekly date window.

Publishing schedule:
  Week 1: Published 8th  → covers 1st-7th
  Week 2: Published 15th → covers 8th-14th
  Week 3: Published 22nd → covers 15th-21st
  Week 4: Published 29th → covers 22nd-28th

When running the scraper, we calculate which week we're in and only
fetch news from that window.
"""

from datetime import date, datetime, timedelta, timezone


def get_current_window(today: date | None = None) -> tuple[date, date]:
    """Return (start_date, end_date) for the current Amber Beat week.

    Based on day of month:
      1-7   → Week 1 window (1st to 7th)
      8-14  → Week 2 window (8th to 14th)
      15-21 → Week 3 window (15th to 21st)
      22-31 → Week 4 window (22nd to 28th)
    """
    if today is None:
        today = datetime.now(timezone.utc).date()

    day = today.day
    year = today.year
    month = today.month

    if day <= 7:
        start = date(year, month, 1)
        end = date(year, month, 7)
    elif day <= 14:
        start = date(year, month, 8)
        end = date(year, month, 14)
    elif day <= 21:
        start = date(year, month, 15)
        end = date(year, month, 21)
    else:
        start = date(year, month, 22)
        end = date(year, month, 28)

    return start, end


def get_google_news_date_param(today: date | None = None) -> str:
    """Return the Google News date filter string for the current week.

    Google News RSS supports 'after:YYYY-MM-DD before:YYYY-MM-DD' syntax
    as well as 'when:Nd'. We use the explicit after/before for precision.
    """
    start, end = get_current_window(today)
    return f"after:{start.isoformat()} before:{(end + timedelta(days=1)).isoformat()}"


def is_within_window(pub_date: datetime | date | None, today: date | None = None) -> bool:
    """Check if a published date falls within the current week window."""
    if pub_date is None:
        return True  # If no date, let it through (LLM will tag it)

    if isinstance(pub_date, datetime):
        pub_date = pub_date.date()

    start, end = get_current_window(today)
    return start <= pub_date <= end


def get_window_label(today: date | None = None) -> str:
    """Return a human-readable label for the current window, e.g. 'Apr Wk 4'."""
    if today is None:
        today = datetime.now(timezone.utc).date()
    start, end = get_current_window(today)
    week_num = (start.day - 1) // 7 + 1
    return f"{start.strftime('%b')} Wk {week_num}"
