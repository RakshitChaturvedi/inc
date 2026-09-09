from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import re


DATE_RE = re.compile(r"(20\d{6})")


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def extract_date(path: Path) -> date | None:
    match = DATE_RE.search(path.name)

    if not match:
        return None

    value = match.group(1)

    try:
        return date(
            int(value[0:4]),
            int(value[4:6]),
            int(value[6:8]),
        )
    except ValueError:
        return None


def existing_dates(output_dir: Path) -> set[date]:
    dates: set[date] = set()

    if not output_dir.exists():
        return dates

    for path in output_dir.glob("*.nc"):
        parsed = extract_date(path)

        if parsed is not None:
            dates.add(parsed)

    return dates


def missing_ranges(
    start: date,
    end: date,
    existing: set[date],
) -> list[tuple[date, date]]:

    missing: list[date] = []

    current = start

    while current <= end:
        if current not in existing:
            missing.append(current)

        current += timedelta(days=1)

    if not missing:
        return []

    ranges: list[tuple[date, date]] = []

    range_start = missing[0]
    previous = missing[0]

    for current in missing[1:]:
        if current == previous + timedelta(days=1):
            previous = current
        else:
            ranges.append((range_start, previous))
            range_start = current
            previous = current

    ranges.append((range_start, previous))

    return ranges