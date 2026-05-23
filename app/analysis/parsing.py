"""Shared ASX HTML parsing utilities.

Normalisers use the scanner contract: YYYY-MM-DD for dates, HH:MM (24hr string) for times.
This is the format expected by datetime.fromisoformat(f"{date} {time}") in the gap strategy.
"""

import contextlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bs4 import Tag


def normalise_date(date_str: str) -> str:
    """Convert DD/MM/YYYY to YYYY-MM-DD (scanner contract).

    Returns empty string on invalid input.
    """
    if not date_str or "/" not in date_str:
        return ""

    try:
        day, month, year = date_str.strip().split("/")
        if not (day.isdigit() and month.isdigit() and year.isdigit()):
            return ""
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    except ValueError:
        return ""


def normalise_time(time_str: str) -> str:
    """Convert 12hr time string to HH:MM (24hr, scanner contract).

    Returns "00:00" on invalid input.
    """
    try:
        time_str = time_str.lower().strip()
        parts = time_str.replace(" pm", "").replace(" am", "").split(":")
        hour = int(parts[0])
        minute = int(parts[1])

        if "pm" in time_str and hour != 12:
            hour += 12
        elif "am" in time_str and hour == 12:
            hour = 0

        return f"{hour:02d}:{minute:02d}"
    except (ValueError, IndexError):
        return "00:00"


def extract_page_count(cell: "Tag") -> int:
    """Extract page count from PDF link cell.

    Returns 1 on any parse failure. Never throws.
    """
    page_span = cell.find("span", class_="page")
    if not page_span:
        return 1

    with contextlib.suppress(ValueError, IndexError):
        return int(page_span.get_text().strip().split()[0])

    return 1
