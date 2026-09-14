from datetime import date

from ocean.acquisition.coverage import (
    CoverageReport,
    FileCoverage,
)
from ocean.acquisition.manifest import (
    build_manifest,
)
from ocean.acquisition.models import (
    AcquisitionChunk,
    BoundingBox,
    DateRange,
)
from ocean.acquisition.request import (
    AcquisitionRequest,
)


def make_request():
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


def make_complete_report():
    file_coverage = FileCoverage(
        path="dummy.nc",
        start=date(2025, 1, 1),
        end=date(2025, 1, 7),
        time_count=7,
        covered_dates=frozenset(
            {
                date(2025, 1, 1),
                date(2025, 1, 2),
                date(2025, 1, 3),
                date(2025, 1, 4),
                date(2025, 1, 5),
                date(2025, 1, 6),
                date(2025, 1, 7),
            }
        ),
    )

    return CoverageReport(
        requested=DateRange(
            start=date(2025, 1, 1),
            end=date(2025, 1, 7),
        ),
        files=(file_coverage,),
        actual_start=date(2025, 1, 1),
        actual_end=date(2025, 1, 7),
        covered_dates=file_coverage.covered_dates,
        missing_dates=frozenset(),
    )


def test_build_manifest():
    request = make_request()

    chunk = AcquisitionChunk(
        index=0,
        start=date(2025, 1, 1),
        end=date(2025, 1, 7),
    )

    report = make_complete_report()

    manifest = build_manifest(
        request,
        [(chunk, report)],
    )

    assert manifest.request_start == "2025-01-01"
    assert manifest.request_end == "2025-01-07"

    assert manifest.variables == ("sst", "sss")

    assert manifest.lat_min == 5.0
    assert manifest.lat_max == 30.0
    assert manifest.lon_min == 45.0
    assert manifest.lon_max == 105.0

    assert len(manifest.chunks) == 1

    manifest_chunk = manifest.chunks[0]

    assert manifest_chunk.index == 0
    assert manifest_chunk.status == "complete"

    assert manifest_chunk.start == "2025-01-01"
    assert manifest_chunk.end == "2025-01-07"

    assert manifest_chunk.missing_dates == ()

    assert len(manifest_chunk.files) == 1
    assert manifest_chunk.files[0].path == "dummy.nc"

def test_manifest_write(tmp_path):
    request = make_request()

    chunk = AcquisitionChunk(
        index=0,
        start=date(2025, 1, 1),
        end=date(2025, 1, 7),
    )

    report = make_complete_report()

    manifest = build_manifest(
        request,
        [(chunk, report)],
    )

    output = tmp_path / "manifest.json"

    manifest.write(output)

    assert output.exists()

    import json

    with output.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    assert data["request_start"] == "2025-01-01"
    assert data["request_end"] == "2025-01-07"
    assert data["variables"] == ["sst", "sss"]

    assert len(data["chunks"]) == 1
    assert data["chunks"][0]["status"] == "complete"

