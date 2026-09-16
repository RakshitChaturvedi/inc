from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path

from ..models import AcquisitionChunk, BoundingBox

class SourceAdapter(ABC):
    # generic interface for remote data source
    @abstractmethod
    def acquire(
        self, *, 
        variables: tuple[str, ...],
        chunk: AcquisitionChunk, 
        region: BoundingBox,
        output_dir: Path
    ) -> list[Path]:
        # acquire data for one temporal chunk
        raise NotImplementedError