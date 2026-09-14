from datetime import date

from ocean.acquisition.models import (
    AcquisitionChunk,
    BoundingBox,
    DateRange,
)


def test_bounding_box():
    region = BoundingBox(
        lat_min=5.0,
        lat_max=30.0,
        lon_min=45.0,
        lon_max=105.0,
    )

    assert region.lat_min == 5.0
    assert region.lat_max == 30.0
    assert region.lon_min == 45.0
    assert region.lon_max == 105.0


def test_date_range():
    date_range = DateRange(
        start=date(2025, 1, 1),
        end=date(2025, 1, 7),
    )

    assert date_range.start == date(2025, 1, 1)
    assert date_range.end == date(2025, 1, 7)


def test_acquisition_chunk():
    chunk = AcquisitionChunk(
        index=0,
        start=date(2025, 1, 1),
        end=date(2025, 1, 7),
    )

    assert chunk.index == 0
    assert chunk.start == date(2025, 1, 1)
    assert chunk.end == date(2025, 1, 7)


def test_acquisition_chunk_identifier():
    chunk = AcquisitionChunk(
        index=0,
        start=date(2025, 1, 1),
        end=date(2025, 1, 7),
    )

    assert chunk.identifier == "2025-01-01_2025-01-07"