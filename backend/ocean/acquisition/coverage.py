from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import xarray as xr
import numpy as np

from .models import DateRange

@dataclass(frozen=True)
class FileCoverage:
    path: Path
    start: date | None
    end: date | None
    time_count: int
    covered_dates: frozenset[date]

@dataclass(frozen=True)
class CoverageReport:
    requested: DateRange
    files: tuple[FileCoverage, ...]
    actual_start: date | None
    actual_end: date | None
    covered_dates: frozenset[date]
    missing_dates: frozenset[date]

    @property
    def is_complete(self) -> bool:
        return not self.missing_dates

    @property
    def has_data(self) -> bool:
        return bool(self.covered_dates)

def _to_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, np.datetime64):
        return value.astype("datetime64[D]").astype(object)
    if hasattr(value, "item"):
        value = value.item()

        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, np.datetime64):
            return value.astype("datetime64[D]").astype(object)

    raise TypeError(f"Unsupported time value type: {type(value).__name__}")

def inspect_file_coverage(path: Path) -> FileCoverage:
    # inspect actual temporal coverage of 1 nc file
    with xr.open_dataset(path) as ds:
        if "time" not in ds.coords and "time" not in ds.variables:
            return FileCoverage(path=path, start=None, end=None, time_count=0, covered_dates=frozenset())
        time_values = ds["time"].values

        if len(time_values) == 0:
            return FileCoverage(path=path, start=None, end=None, time_count=0, covered_dates=frozenset())
        dates = [_to_date(value) for value in time_values]
        return FileCoverage(path=path, start=min(dates), end=max(dates), time_count=len(dates), 
                            covered_dates=frozenset(dates))

def build_coverage_report(files: list[Path], requested: DateRange) -> CoverageReport:
    # inspect all supplied files and build a temporal coverage report

    file_reports = tuple(inspect_file_coverage(path) for path in files)
    covered_dates: set[date] = set()
    for report in file_reports:
        if report.start is None or report.end is None:
            continue
        current = report.start
        while current <= report.end:
            covered_dates.add(current)
            current = current.fromordinal(current.toordinal()+1)

    requested_dates: set[date] = set()
    current = requested.start
    while current <= requested.end:
        requested_dates.add(current)
        current = current.fromordinal(current.toordinal()+1)

    relevant_covered_dates = (covered_dates & requested_dates)
    missing_dates = (requested_dates - relevant_covered_dates)
    actual_dates = sorted(relevant_covered_dates)

    actual_start = actual_dates[0] if actual_dates else None
    actual_end = actual_dates[-1] if actual_dates else None

    return CoverageReport(
        requested=requested,
        files=file_reports,
        actual_start=actual_start,
        actual_end=actual_end,
        covered_dates=frozenset(relevant_covered_dates),
        missing_dates=frozenset(missing_dates)
    )