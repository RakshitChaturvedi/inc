from datetime import date

import numpy as np
import xarray as xr

from ocean.acquisition.coverage import (
    build_coverage_report,
    inspect_file_coverage,
)
from ocean.acquisition.models import DateRange


def create_test_netcdf(
    path,
    dates,
):
    ds = xr.Dataset(
        {
            "sst": (
                ("time", "lat", "lon"),
                np.ones((len(dates), 1, 1)),
            )
        },
        coords={
            "time": dates,
            "lat": [10.0],
            "lon": [70.0],
        },
    )

    ds.to_netcdf(path)


def test_inspect_file_coverage(tmp_path):
    path = tmp_path / "test.nc"

    dates = [
        np.datetime64("2025-01-01"),
        np.datetime64("2025-01-02"),
        np.datetime64("2025-01-03"),
    ]

    create_test_netcdf(path, dates)

    coverage = inspect_file_coverage(path)

    assert coverage.path == path
    assert coverage.start == date(2025, 1, 1)
    assert coverage.end == date(2025, 1, 3)
    assert coverage.time_count == 3

def test_build_coverage_report(tmp_path):
    file_1 = tmp_path / "file_1.nc"
    file_2 = tmp_path / "file_2.nc"

    create_test_netcdf(
        file_1,
        [
            np.datetime64("2025-01-01"),
            np.datetime64("2025-01-02"),
        ],
    )

    create_test_netcdf(
        file_2,
        [
            np.datetime64("2025-01-03"),
            np.datetime64("2025-01-04"),
        ],
    )

    requested = DateRange(
        start=date(2025, 1, 1),
        end=date(2025, 1, 4),
    )

    report = build_coverage_report(
        [file_1, file_2],
        requested,
    )

    assert report.actual_start == date(2025, 1, 1)
    assert report.actual_end == date(2025, 1, 4)

    assert report.covered_dates == frozenset(
        {
            date(2025, 1, 1),
            date(2025, 1, 2),
            date(2025, 1, 3),
            date(2025, 1, 4),
        }
    )

    assert report.missing_dates == frozenset()

    assert report.is_complete
    assert report.has_data

def test_partial_coverage(tmp_path):
    path = tmp_path / "partial.nc"

    create_test_netcdf(
        path,
        [
            np.datetime64("2025-01-01"),
            np.datetime64("2025-01-02"),
            np.datetime64("2025-01-03"),
        ],
    )

    requested = DateRange(
        start=date(2025, 1, 1),
        end=date(2025, 1, 5),
    )

    report = build_coverage_report(
        [path],
        requested,
    )

    assert report.actual_start == date(2025, 1, 1)
    assert report.actual_end == date(2025, 1, 3)

    assert report.missing_dates == frozenset(
        {
            date(2025, 1, 4),
            date(2025, 1, 5),
        }
    )

    assert not report.is_complete
    assert report.has_data

def test_file_without_time_coordinate(tmp_path):
    path = tmp_path / "no_time.nc"

    ds = xr.Dataset(
        {
            "sst": (
                ("lat", "lon"),
                np.ones((1, 1)),
            )
        },
        coords={
            "lat": [10.0],
            "lon": [70.0],
        },
    )

    ds.to_netcdf(path)

    coverage = inspect_file_coverage(path)

    assert coverage.start is None
    assert coverage.end is None
    assert coverage.time_count == 0