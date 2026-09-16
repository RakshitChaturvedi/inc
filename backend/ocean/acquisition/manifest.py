from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

from .coverage import CoverageReport
from .models import AcquisitionChunk
from .request import AcquisitionRequest

@dataclass(frozen=True)
class ManifestFile:
    path: str
    start: str | None
    end: str | None
    time_count: int
    covered_dates: tuple[str, ...]

@dataclass(frozen=True)
class ManifestChunk:
    index: int
    start: str
    end: str
    status: str
    files: tuple[ManifestFile, ...]
    covered_dates: tuple[str, ...]
    missing_dates: tuple[str, ...]

@dataclass(frozen=True)
class AcquisitionManifest:
    created_at: str
    request_start: str
    request_end: str
    variables: tuple[str, ...]
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    chunk_days: int
    chunks: tuple[ManifestChunk, ...]

    def to_dict(self) -> dict:
        return asdict(self)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(),handle,indent=2)

def _date_strings(values: set[date] | frozenset[date]) -> tuple[str, ...]:
    return tuple(value.isoformat() for value in sorted(values))

def _file_manifest(coverage_file) -> ManifestFile:
    return ManifestFile(
        path=str(coverage_file.path),
        start=(
            coverage_file.start.isoformat()
            if coverage_file.start is not None else None
        ),
        end=(
            coverage_file.end.isoformat()
            if coverage_file.end is not None else None
        ),
        time_count=coverage_file.time_count,
        covered_dates=_date_strings(coverage_file.covered_dates)
    )

def _chunk_status(report: CoverageReport) -> str:
    if not report.has_data:
        return "unavailable"

    if report.is_complete:
        return "complete"

    return "partial"

def build_manifest_chunk(chunk: AcquisitionChunk,report: CoverageReport) -> ManifestChunk:
    return ManifestChunk(
        index=chunk.index,
        start=chunk.start.isoformat(),
        end=chunk.end.isoformat(),
        status=_chunk_status(report),
        files=tuple(_file_manifest(file_coverage) for file_coverage in report.files),
        covered_dates=_date_strings(report.covered_dates),
        missing_dates=_date_strings(report.missing_dates),
    )

def build_manifest(
    request: AcquisitionRequest,
    chunks: list[tuple[AcquisitionChunk, CoverageReport]],
) -> AcquisitionManifest:
    return AcquisitionManifest(
        created_at=datetime.now().astimezone().isoformat(),
        request_start=request.date_range.start.isoformat(),
        request_end=request.date_range.end.isoformat(),
        variables=request.variables,
        lat_min=request.region.lat_min,
        lat_max=request.region.lat_max,
        lon_min=request.region.lon_min,
        lon_max=request.region.lon_max,
        chunk_days=request.chunk_days,
        chunks=tuple(
            build_manifest_chunk(
                chunk,
                report,
            )
            for chunk, report in chunks
        ),
    )