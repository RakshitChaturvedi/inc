from datetime import date

import pytest

from ocean.acquisition.models import BoundingBox, DateRange
from ocean.acquisition.request import (
    AcquisitionRequest,
    validate_request,
)


def make_valid_request() -> AcquisitionRequest:
    return AcquisitionRequest(
        date_range=DateRange(
            start=date(2025, 1, 1),
            end=date(2025, 1, 7),
        ),
        region=BoundingBox(
            lat_min=5.0,
            lat_max=30.0,
            lon_min=45.0,
            lon_max=105.0,
        ),
        variables=("sst", "sss"),
        chunk_days=7,
    )


def test_valid_request():
    request = make_valid_request()

    validate_request(request)


def test_invalid_date_range():
    request = make_valid_request()

    request = AcquisitionRequest(
        date_range=DateRange(
            start=date(2025, 1, 8),
            end=date(2025, 1, 1),
        ),
        region=request.region,
        variables=request.variables,
        chunk_days=request.chunk_days,
    )

    with pytest.raises(ValueError, match="start date"):
        validate_request(request)


def test_invalid_latitude_range():
    request = make_valid_request()

    request = AcquisitionRequest(
        date_range=request.date_range,
        region=BoundingBox(
            lat_min=30.0,
            lat_max=5.0,
            lon_min=45.0,
            lon_max=105.0,
        ),
        variables=request.variables,
        chunk_days=request.chunk_days,
    )

    with pytest.raises(ValueError, match="lat_min"):
        validate_request(request)


def test_invalid_longitude_range():
    request = make_valid_request()

    request = AcquisitionRequest(
        date_range=request.date_range,
        region=BoundingBox(
            lat_min=5.0,
            lat_max=30.0,
            lon_min=105.0,
            lon_max=45.0,
        ),
        variables=request.variables,
        chunk_days=7,
    )

    with pytest.raises(ValueError, match="lon_min"):
        validate_request(request)


def test_invalid_chunk_size():
    request = make_valid_request()

    request = AcquisitionRequest(
        date_range=request.date_range,
        region=request.region,
        variables=request.variables,
        chunk_days=0,
    )

    with pytest.raises(ValueError, match="chunk_days"):
        validate_request(request)


def test_empty_variables():
    request = make_valid_request()

    request = AcquisitionRequest(
        date_range=request.date_range,
        region=request.region,
        variables=(),
        chunk_days=7,
    )

    with pytest.raises(ValueError, match="variable"):
        validate_request(request)