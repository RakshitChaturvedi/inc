from datetime import date
from pathlib import Path

import numpy as np
import xarray as xr

from ocean.acquisition.adapters.base import SourceAdapter
from ocean.acquisition.models import (
    AcquisitionChunk,
    BoundingBox,
)
from ocean.acquisition.request import AcquisitionRequest
from ocean.acquisition.models import DateRange
from ocean.acquisition.service import AcquisitionService


class FakeAdapter(SourceAdapter):
    def __init__(self):
        self.calls = []

    def acquire(
        self,
        *,
        variables: tuple[str, ...],
        chunk: AcquisitionChunk,
        region: BoundingBox,
        output_dir: Path,
    ) -> list[Path]:

        self.calls.append(
            {
                "variables": variables,
                "chunk": chunk,
                "region": region,
                "output_dir": output_dir,
            }
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        dates = []
        current = chunk.start

        while current <= chunk.end:
            dates.append(
                np.datetime64(current.isoformat())
            )
            current = date.fromordinal(
                current.toordinal() + 1
            )

        files = []

        for variable in variables:
            path = (
                output_dir
                / f"{variable}_{chunk.identifier}.nc"
            )

            ds = xr.Dataset(
                {
                    variable: (
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
            files.append(path)

        return files

def make_request():
    return AcquisitionRequest(
        date_range=DateRange(
            start=date(2025, 1, 1),
            end=date(2025, 1, 14),
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

def test_service_acquires_all_chunks(tmp_path):
    adapter = FakeAdapter()

    service = AcquisitionService(
        adapter=adapter,
        output_dir=tmp_path / "output",
    )

    manifest = service.acquire(
        make_request()
    )

    assert len(adapter.calls) == 2

    assert len(manifest.chunks) == 2

    assert manifest.chunks[0].status == "complete"
    assert manifest.chunks[1].status == "complete"

    assert manifest.chunks[0].start == "2025-01-01"
    assert manifest.chunks[0].end == "2025-01-07"

    assert manifest.chunks[1].start == "2025-01-08"
    assert manifest.chunks[1].end == "2025-01-14"

def test_service_passes_request_to_adapter(tmp_path):
    adapter = FakeAdapter()

    service = AcquisitionService(
        adapter=adapter,
        output_dir=tmp_path / "output",
    )

    request = make_request()

    service.acquire(request)

    assert len(adapter.calls) == 2

    for call in adapter.calls:
        assert call["variables"] == (
            "sst",
            "sss",
        )

        assert call["region"] == request.region

def test_service_passes_correct_chunks(tmp_path):
    adapter = FakeAdapter()

    service = AcquisitionService(
        adapter=adapter,
        output_dir=tmp_path / "output",
    )

    service.acquire(make_request())

    assert adapter.calls[0]["chunk"].start == date(
        2025, 1, 1
    )

    assert adapter.calls[0]["chunk"].end == date(
        2025, 1, 7
    )

    assert adapter.calls[1]["chunk"].start == date(
        2025, 1, 8
    )

    assert adapter.calls[1]["chunk"].end == date(
        2025, 1, 14
    )

def test_service_uses_chunk_output_directories(tmp_path):
    adapter = FakeAdapter()

    output_dir = tmp_path / "output"

    service = AcquisitionService(
        adapter=adapter,
        output_dir=output_dir,
    )

    service.acquire(make_request())

    first_output = adapter.calls[0]["output_dir"]
    second_output = adapter.calls[1]["output_dir"]

    assert first_output == (
        output_dir / "2025-01-01_2025-01-07"
    )

    assert second_output == (
        output_dir / "2025-01-08_2025-01-14"
    )

    assert first_output.exists()
    assert second_output.exists()

def test_service_writes_manifest(tmp_path):
    output_dir = tmp_path / "output"

    adapter = FakeAdapter()

    service = AcquisitionService(
        adapter=adapter,
        output_dir=output_dir,
    )

    service.acquire(make_request())

    manifest_path = output_dir / "manifest.json"

    assert manifest_path.exists()

class PartialFakeAdapter(FakeAdapter):
    def acquire(
        self,
        *,
        variables: tuple[str, ...],
        chunk: AcquisitionChunk,
        region: BoundingBox,
        output_dir: Path,
    ) -> list[Path]:

        self.calls.append(
            {
                "variables": variables,
                "chunk": chunk,
                "region": region,
                "output_dir": output_dir,
            }
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        end = min(
            chunk.start.toordinal() + 2,
            chunk.end.toordinal(),
        )

        dates = []

        current = chunk.start

        while current.toordinal() <= end:
            dates.append(
                np.datetime64(current.isoformat())
            )

            current = date.fromordinal(
                current.toordinal() + 1
            )

        path = output_dir / "partial.nc"

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

        return [path]

def test_service_records_partial_coverage(tmp_path):
    adapter = PartialFakeAdapter()

    service = AcquisitionService(
        adapter=adapter,
        output_dir=tmp_path / "output",
    )

    manifest = service.acquire(
        make_request()
    )

    assert len(manifest.chunks) == 2

    assert manifest.chunks[0].status == "partial"
    assert manifest.chunks[1].status == "partial"

    assert len(
        manifest.chunks[0].missing_dates
    ) == 4

    assert len(
        manifest.chunks[1].missing_dates
    ) == 4

class UnavailableFakeAdapter(FakeAdapter):
    def acquire(
        self,
        *,
        variables: tuple[str, ...],
        chunk: AcquisitionChunk,
        region: BoundingBox,
        output_dir: Path,
    ) -> list[Path]:

        self.calls.append(
            {
                "variables": variables,
                "chunk": chunk,
                "region": region,
                "output_dir": output_dir,
            }
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        return []

def test_service_records_unavailable_coverage(tmp_path):
    adapter = UnavailableFakeAdapter()

    service = AcquisitionService(
        adapter=adapter,
        output_dir=tmp_path / "output",
    )

    manifest = service.acquire(
        make_request()
    )

    assert len(manifest.chunks) == 2

    assert manifest.chunks[0].status == "unavailable"
    assert manifest.chunks[1].status == "unavailable"

