"""Documented query durations and conservative adapter window bounds."""

import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from .diagnostic_inputs import instant

if TYPE_CHECKING:
    from .query_inputs import QueryInput

MAX_WINDOW = timedelta(days=90)


def query_time(value: str, *, source_utc: bool = False) -> datetime:
    offset = r"(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
    pattern = (
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}"
        r"(?:\.0+)?" + (offset + "?" if source_utc else offset)
    )
    if not re.fullmatch(pattern, value):
        raise ValueError("Query dates require whole seconds and a valid explicit offset")
    return instant(value, source_utc=source_utc)


def normalize_period(period: str | None, days: int | None) -> tuple[str, timedelta]:
    if period is not None and days is not None:
        raise ValueError("Choose period or legacy period_days, not both")
    text = period if period is not None else f"{days if days is not None else 1}d"
    if len(text) > 16 or not re.fullmatch(r"[1-9][0-9]*[mhd]?", text):
        raise ValueError("Period must be positive integer text with optional m/h/d suffix")
    unit = text[-1] if text[-1] in "mhd" else "d"
    number = int(text[:-1] if text[-1] in "mhd" else text)
    seconds = number * {"m": 60, "h": 3600, "d": 86400}[unit]
    if seconds > 90 * 86400:
        raise ValueError("Query period exceeds the adapter 90-day bound")
    return f"{number}{unit}", timedelta(seconds=seconds)


def validate_bounds(start: str | None, end: str | None) -> None:
    if end is None:
        return
    if start is None:
        raise ValueError("end_date requires start_date")
    span = instant(end) - instant(start)
    if not timedelta(0) < span <= MAX_WINDOW:
        raise ValueError("Query window must be positive and at most 90 days")


def check_window(request: "QueryInput", start: datetime, end: datetime) -> None:
    if start.microsecond or end.microsecond or start >= end:
        raise ValueError("Invalid source query window")
    if request.start_date is not None and start != instant(request.start_date):
        raise ValueError("Source query start differs from requested start")
    if request.end_date is not None:
        if end != instant(request.end_date):
            raise ValueError("Source query end differs from requested end")
    elif end - start != normalize_period(request.period, request.period_days)[1]:
        raise ValueError("Source query duration differs from requested period")
