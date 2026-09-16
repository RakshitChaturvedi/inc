from __future__ import annotations

from pathlib import Path

from .adapters.base import SourceAdapter
from .chunking import build_chunks
from .coverage import build_coverage_report
from .manifest import AcquisitionManifest, build_manifest
from .models import DateRange
from .request import AcquisitionRequest, validate_request

class AcquisitionService:
    # provider-independent acq orchestrator, provider specific logic belongs to Sourceadapter
    def __init__(
            self,
            adapter: SourceAdapter,
            output_dir: Path,
            manifest_path: Path | None = None
    ) -> None:
        self.adapter = adapter
        self.output_dir = output_dir
        self.manifest_path = (manifest_path if manifest_path is not None else self.output_dir / "manifest.json")

    def acquire(self, request: AcquisitionRequest) -> AcquisitionManifest:
        # execute request
        validate_request(request)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        chunks = build_chunks(request.date_range, request.chunk_days)
        chunk_reports = []

        for chunk in chunks:
            chunk_output_dir = (self.output_dir / chunk.identifier)
            chunk_output_dir.mkdir(parents=True, exist_ok=True)
            files = self.adapter.acquire(
                variables=request.variables, chunk=chunk,
                region=request.region, output_dir=chunk_output_dir
            )
            coverage=build_coverage_report(files, requested=DateRange(start=chunk.start, end=chunk.end))
            chunk_reports.append((chunk, coverage))

        manifest = build_manifest(request, chunk_reports)
        manifest.write(self.manifest_path)

        return manifest
        