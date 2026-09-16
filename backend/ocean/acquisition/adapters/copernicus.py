from __future__ import annotations
from pathlib import Path

from ..copernicus import acquire_variable
from ..models import AcquisitionChunk, BoundingBox
from .base import SourceAdapter

class CopernicusAdapter(SourceAdapter):
    def __init__(self, sources: dict[str, dict]) -> None:
        self.sources = sources

    def acquire(self, *, variables: tuple[str, ...],
                chunk: AcquisitionChunk, region: BoundingBox,
                output_dir: Path) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        files: list[Path] = []

        for variable in variables:
            if variable not in self.sources:
                raise ValueError(f"No copernicus config found for variable: {variable}")
            source = dict(self.sources[variable])
            source["output_dir"] = str(output_dir/variable)
            path = acquire_variable(
                source=source, 
                variable=variable,
                start=chunk.start.isoformat(),
                end=chunk.end.isoformat(), 
                bbox={
                    "lat_min": region.lat_min,
                    "lat_max": region.lat_max,
                    "lon_min": region.lon_min,
                    "lon_max": region.lon_max,
                }
            )
            files.append(path)

        return sorted(path.resolve() for path in files)