from __future__ import annotations

import re
from datetime import UTC, datetime

from raqe.models.time_context import TimeContext

QUARTER_FY_PATTERN = re.compile(r"\bQ([1-4])\s*FY(\d{2,4})\b", re.IGNORECASE)
FY_QUARTER_PATTERN = re.compile(r"\bFY(\d{2,4})\s*Q([1-4])\b", re.IGNORECASE)
FY_PATTERN = re.compile(r"\bFY(\d{2,4})\b", re.IGNORECASE)
DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
BETWEEN_RANGE_PATTERN = re.compile(
    r"\bbetween\s+(\d{4}-\d{2}-\d{2})\s+and\s+(\d{4}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)
LAST_N_QUARTERS_PATTERN = re.compile(r"\blast\s+(\d+)\s+quarters?\b", re.IGNORECASE)


def _normalize_fiscal_year(value: str) -> str:
    digits = value.strip()
    if len(digits) == 2:
        return f"FY20{digits}"
    if len(digits) == 4:
        return f"FY{digits}"
    return f"FY{digits}"


def parse_time(question: str, now: datetime | None = None) -> TimeContext:
    text = question.strip()
    lowered = text.lower()

    match = BETWEEN_RANGE_PATTERN.search(text)
    if match:
        start_date, end_date = match.groups()
        return TimeContext(
            raw_text=text,
            mode="explicit_range",
            start_date=start_date,
            end_date=end_date,
            needs_fallback=False,
        )

    date_values = DATE_PATTERN.findall(text)
    if len(date_values) == 2:
        return TimeContext(
            raw_text=text,
            mode="explicit_range",
            start_date=date_values[0],
            end_date=date_values[1],
            needs_fallback=False,
        )
    if len(date_values) == 1:
        return TimeContext(
            raw_text=text,
            mode="explicit_range",
            start_date=date_values[0],
            end_date=date_values[0],
            needs_fallback=False,
        )

    qfy_match = QUARTER_FY_PATTERN.search(text)
    if qfy_match:
        quarter, fy_digits = qfy_match.groups()
        return TimeContext(
            raw_text=text,
            mode="quarter",
            period=f"Q{quarter}",
            fiscal_year=_normalize_fiscal_year(fy_digits),
            needs_fallback=False,
        )

    fyq_match = FY_QUARTER_PATTERN.search(text)
    if fyq_match:
        fy_digits, quarter = fyq_match.groups()
        return TimeContext(
            raw_text=text,
            mode="quarter",
            period=f"Q{quarter}",
            fiscal_year=_normalize_fiscal_year(fy_digits),
            needs_fallback=False,
        )

    last_n_match = LAST_N_QUARTERS_PATTERN.search(text)
    if last_n_match:
        return TimeContext(
            raw_text=text,
            mode="relative",
            relative_window=f"last_{last_n_match.group(1)}_quarters",
            needs_fallback=False,
        )

    if "last quarter" in lowered:
        return TimeContext(
            raw_text=text,
            mode="relative",
            relative_window="last_quarter",
            needs_fallback=False,
        )

    if "last year" in lowered:
        return TimeContext(
            raw_text=text,
            mode="relative",
            relative_window="last_year",
            needs_fallback=False,
        )

    fy_match = FY_PATTERN.search(text)
    if fy_match:
        return TimeContext(
            raw_text=text,
            mode="year",
            fiscal_year=_normalize_fiscal_year(fy_match.group(1)),
            needs_fallback=False,
        )

    year_match = re.search(r"\b(20\d{2})\b", text)
    if year_match:
        return TimeContext(
            raw_text=text,
            mode="year",
            fiscal_year=f"FY{year_match.group(1)}",
            needs_fallback=False,
        )

    if "latest" in lowered or "recent" in lowered:
        return TimeContext(
            raw_text=text,
            mode="latest_fallback",
            relative_window="latest",
            needs_fallback=True,
        )

    _ = now or datetime.now(UTC)
    return TimeContext(
        raw_text=text,
        mode="latest_fallback",
        relative_window="latest",
        needs_fallback=True,
    )
