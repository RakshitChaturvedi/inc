from datetime import date
from pathlib import Path
import pytest

from ocean.acquisition.adapters.base import SourceAdapter
from ocean.acquisition.models import (
    AcquisitionChunk,
    BoundingBox,
)


class FakeAdapter(SourceAdapter):

    def acquire(
        self,
        *,
        variables: tuple[str, ...],
        chunk: AcquisitionChunk,
        region: BoundingBox,
        output_dir: Path,
    ) -> list[Path]:

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        files = []

        for variable in variables:
            path = output_dir / (
                f"{variable}_{chunk.identifier}.nc"
            )

            path.touch()
            files.append(path)

        return files

def test_source_adapter_is_abstract():
    with pytest.raises(TypeError):
        SourceAdapter()

def test_fake_adapter_implements_source_adapter(tmp_path):
    adapter = FakeAdapter()

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
        variables=("sst", "sss"),
        chunk=chunk,
        region=region,
        output_dir=tmp_path,
    )

    assert len(files) == 2

    assert files[0] == (
        tmp_path / "sst_2025-01-01_2025-01-07.nc"
    )

    assert files[1] == (
        tmp_path / "sss_2025-01-01_2025-01-07.nc"
    )

    assert all(path.exists() for path in files)