from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from ocean.acquisition.adapters.copernicus import CopernicusAdapter
from ocean.acquisition.models import AcquisitionChunk, BoundingBox


def test_copernicus_adapter_passes_configuration_and_chunk(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    def fake_acquire_variable(
        *,
        source: dict,
        variable: str,
        start: str,
        end: str,
        bbox: dict[str, float],
    ) -> Path:
        calls.append(
            {
                "source": source,
                "variable": variable,
                "start": start,
                "end": end,
                "bbox": bbox,
            }
        )

        path = Path(source["output_dir"]) / f"{variable}.nc"
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.touch()

        return path

    monkeypatch.setattr(
        "ocean.acquisition.adapters.copernicus.acquire_variable",
        fake_acquire_variable,
    )

    sources = {
        "sst": {
            "enabled": True,
            "product_id": (
                "SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001"
            ),
            "preferred_variables": (
                "analysed_sst",
            ),
            "output_dir": "data/raw/sst",
        }
    }

    adapter = CopernicusAdapter(
        sources=sources,
    )

    chunk = AcquisitionChunk(
        index=0,
        start=date(2025, 1, 1),
        end=date(2025, 1, 7),
    )

    region = BoundingBox(
        lat_min=5.0,
        lat_max=30.0,
        lon_min=45.0,
        lon_max=105.0,
    )

    files = adapter.acquire(
        variables=("sst",),
        chunk=chunk,
        region=region,
        output_dir=tmp_path,
    )

    assert len(calls) == 1

    assert calls[0]["variable"] == "sst"

    assert calls[0]["start"] == "2025-01-01"
    assert calls[0]["end"] == "2025-01-07"

    assert calls[0]["bbox"] == {
        "lat_min": 5.0,
        "lat_max": 30.0,
        "lon_min": 45.0,
        "lon_max": 105.0,
    }

    assert calls[0]["source"]["product_id"] == (
        "SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001"
    )

    assert calls[0]["source"]["preferred_variables"] == (
        "analysed_sst",
    )

    # The adapter must override the YAML output directory
    # with the chunk-specific output directory.
    assert calls[0]["source"]["output_dir"] == str(
        tmp_path / "sst"
    )

    assert len(files) == 1
    assert files[0].name == "sst.nc"


def test_copernicus_adapter_supports_multiple_variables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    def fake_acquire_variable(
        *,
        source: dict,
        variable: str,
        start: str,
        end: str,
        bbox: dict[str, float],
    ) -> Path:
        calls.append(
            {
                "source": source,
                "variable": variable,
                "start": start,
                "end": end,
                "bbox": bbox,
            }
        )

        path = Path(source["output_dir"]) / f"{variable}.nc"
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.touch()

        return path

    monkeypatch.setattr(
        "ocean.acquisition.adapters.copernicus.acquire_variable",
        fake_acquire_variable,
    )

    sources = {
        "sst": {
            "enabled": True,
            "product_id": "SST_PRODUCT",
            "preferred_variables": (
                "analysed_sst",
            ),
            "output_dir": "data/raw/sst",
        },
        "ssh": {
            "enabled": True,
            "product_id": "SEALEVEL_PRODUCT",
            "preferred_variables": (
                "sla",
            ),
            "output_dir": "data/raw/ssh",
        },
    }

    adapter = CopernicusAdapter(
        sources=sources,
    )

    chunk = AcquisitionChunk(
        index=1,
        start=date(2025, 1, 8),
        end=date(2025, 1, 14),
    )

    region = BoundingBox(
        lat_min=5.0,
        lat_max=30.0,
        lon_min=45.0,
        lon_max=105.0,
    )

    files = adapter.acquire(
        variables=("sst", "ssh"),
        chunk=chunk,
        region=region,
        output_dir=tmp_path,
    )

    assert [call["variable"] for call in calls] == [
        "sst",
        "ssh",
    ]

    assert [
        call["source"]["product_id"]
        for call in calls
    ] == [
        "SST_PRODUCT",
        "SEALEVEL_PRODUCT",
    ]

    assert all(
        call["start"] == "2025-01-08"
        for call in calls
    )

    assert all(
        call["end"] == "2025-01-14"
        for call in calls
    )

    assert calls[0]["source"]["output_dir"] == str(
        tmp_path / "sst"
    )

    assert calls[1]["source"]["output_dir"] == str(
        tmp_path / "ssh"
    )

    assert len(files) == 2


def test_copernicus_adapter_rejects_unknown_variable(
    tmp_path: Path,
) -> None:
    adapter = CopernicusAdapter(
        sources={
            "sst": {
                "enabled": True,
                "product_id": "SST_PRODUCT",
                "preferred_variables": (
                    "analysed_sst",
                ),
                "output_dir": "data/raw/sst",
            }
        }
    )

    chunk = AcquisitionChunk(
        index=0,
        start=date(2025, 1, 1),
        end=date(2025, 1, 7),
    )

    region = BoundingBox(
        lat_min=5.0,
        lat_max=30.0,
        lon_min=45.0,
        lon_max=105.0,
    )

    with pytest.raises(
        ValueError,
        match="No copernicus config found",
    ):
        adapter.acquire(
            variables=("ssh",),
            chunk=chunk,
            region=region,
            output_dir=tmp_path,
        )