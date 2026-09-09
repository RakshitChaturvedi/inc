# backend/api/dates.py

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Iterable


def resolve_week(value: date | datetime | str) -> str:
    """
    Convert a date/datetime/ISO date string to an ISO-8601 week.

    Example:
        2026-09-03 -> 2026-W36
    """

    if isinstance(value, datetime):
        value = value.date()

    elif isinstance(value, str):
        try:
            value = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                f"Invalid date '{value}'. Expected YYYY-MM-DD."
            ) from exc

    if not isinstance(value, date):
        raise TypeError(
            f"Expected date, datetime, or ISO date string; got {type(value).__name__}"
        )

    iso = value.isocalendar()

    return f"{iso.year}-W{iso.week:02d}"


def normalize_date(value: date | datetime | str) -> date:
    """
    Normalize a date-like value to datetime.date.
    """

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                f"Invalid date '{value}'. Expected YYYY-MM-DD."
            ) from exc

    raise TypeError(
        f"Expected date, datetime, or ISO date string; got {type(value).__name__}"
    )


def date_to_iso(value: date | datetime | str) -> str:
    """
    Return a normalized YYYY-MM-DD representation.
    """

    return normalize_date(value).isoformat()


def get_available_dates(
    times: Iterable,
) -> list[date]:
    """
    Convert an iterable of xarray/pandas/numpy-like timestamps into
    unique Python dates.

    Primarily useful for validating API requests against the dashboard
    dataset's time coordinate.
    """

    dates: set[date] = set()

    for value in times:
        if hasattr(value, "date"):
            converted = value.date()
        else:
            converted = date.fromisoformat(str(value)[:10])

        dates.add(converted)

    return sorted(dates)


def is_date_available(
    requested: date | datetime | str,
    times: Iterable,
) -> bool:
    """
    Check whether a requested calendar date exists in the dataset.
    """

    requested_date = normalize_date(requested)

    return requested_date in set(get_available_dates(times))