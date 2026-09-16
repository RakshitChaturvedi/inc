from datetime import date

import numpy as np
import xarray as xr

from ocean.acquisition.coverage import (
    build_coverage_report,
)
from ocean.acquisition.models import (
    BoundingBox,
    DateRange,
)
from ocean.acquisition.validation import (
    validate_acquisition,
)


REGION = BoundingBox(
    lat_min=5.0,
    lat_max=30.0,
    lon_min=45.0,
    lon_max=105.0,
)


def create_test_netcdf(
    path,
    variables=("sst",),
    dates=(
        np.datetime64("2025-01-01"),
        np.datetime64("2025-01-02"),
    ),
):
    data_vars = {}

    for variable in variables:
        data_vars[variable] = (
            ("time", "lat", "lon"),
            np.ones((len(dates), 2, 2)),
        )

    ds = xr.Dataset(
        data_vars,
        coords={
            "time": np.asarray(dates),
            "lat": np.asarray([10.0, 20.0]),
            "lon": np.asarray([60.0, 70.0]),
        }
    )

    ds.to_netcdf(path)


def make_coverage(files):
    return build_coverage_report(
        files,
        DateRange(
            start=date(2025, 1, 1),
            end=date(2025, 1, 2),
        ),
    )

def test_valid_acquisition(tmp_path):
    path = tmp_path / "valid.nc"

    create_test_netcdf(
        path,
        variables=("sst", "sss"),
    )

    coverage = make_coverage([path])

    result = validate_acquisition(
        files=[path],
        required_variables=("sst", "sss"),
        region=REGION,
        coverage=coverage,
    )

    assert result.valid
    assert not result.errors
    assert not result.warnings

def test_missing_required_variable(tmp_path):
    path = tmp_path / "missing_sss.nc"

    create_test_netcdf(
        path,
        variables=("sst",),
    )

    coverage = make_coverage([path])

    result = validate_acquisition(
        files=[path],
        required_variables=("sst", "sss"),
        region=REGION,
        coverage=coverage,
    )

    assert not result.valid

    assert any(
        "sss" in error
        for error in result.errors
    )

def test_missing_required_variable(tmp_path):
    path = tmp_path / "missing_sss.nc"

    create_test_netcdf(
        path,
        variables=("sst",),
    )

    coverage = make_coverage([path])

    result = validate_acquisition(
        files=[path],
        required_variables=("sst", "sss"),
        region=REGION,
        coverage=coverage,
    )

    assert not result.valid

    assert any(
        "sss" in error
        for error in result.errors
    )

def test_missing_time_coordinate(tmp_path):
    path = tmp_path / "no_time.nc"

    ds = xr.Dataset(
        {
            "sst": (
                ("lat", "lon"),
                np.ones((2, 2)),
            )
        },
        coords={
            "lat": [10.0, 20.0],
            "lon": [60.0, 70.0],
        },
    )

    ds.to_netcdf(path)

    coverage = build_coverage_report(
        [path],
        DateRange(
            start=date(2025, 1, 1),
            end=date(2025, 1, 2),
        ),
    )

    result = validate_acquisition(
        files=[path],
        required_variables=("sst",),
        region=REGION,
        coverage=coverage,
    )

    assert not result.valid

    assert any(
        "time coordinate" in error
        for error in result.errors
    )

def test_partial_temporal_coverage_is_warning(tmp_path):
    path = tmp_path / "partial.nc"

    create_test_netcdf(
        path,
        variables=("sst",),
        dates=(
            np.datetime64("2025-01-01"),
        ),
    )

    coverage = build_coverage_report(
        [path],
        DateRange(
            start=date(2025, 1, 1),
            end=date(2025, 1, 2),
        ),
    )

    result = validate_acquisition(
        files=[path],
        required_variables=("sst",),
        region=REGION,
        coverage=coverage,
    )

    assert result.valid

    assert any(
        "incomplete" in warning
        for warning in result.warnings
    )

def test_no_temporal_coverage_is_error(tmp_path):
    coverage = build_coverage_report(
        [],
        DateRange(
            start=date(2025, 1, 1),
            end=date(2025, 1, 2),
        ),
    )

    result = validate_acquisition(
        files=[],
        required_variables=("sst",),
        region=REGION,
        coverage=coverage,
    )

    assert not result.valid

    assert any(
        "No temporal coverage" in error
        for error in result.errors
    )

def test_spatial_mismatch(tmp_path):
    path = tmp_path / "outside_region.nc"

    ds = xr.Dataset(
        {
            "sst": (
                ("time", "lat", "lon"),
                np.ones((2, 2, 2)),
            )
        },
        coords={
            "time": [
                np.datetime64("2025-01-01"),
                np.datetime64("2025-01-02"),
            ],
            "lat": [-30.0, -20.0],
            "lon": [60.0, 70.0],
        },
    )

    ds.to_netcdf(path)

    coverage = make_coverage([path])

    result = validate_acquisition(
        files=[path],
        required_variables=("sst",),
        region=REGION,
        coverage=coverage,
    )

    assert not result.valid

    assert any(
        "Latitude coverage" in error
        for error in result.errors
    )

