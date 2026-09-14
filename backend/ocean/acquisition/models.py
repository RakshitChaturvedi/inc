from __future__ import annotations
from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class BoundingBox:
    # geographic region for acquisition
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float

@dataclass(frozen=True)
class DateRange:
    start: date
    end: date

@dataclass(frozen=True)
class AcquisitionChunk:
    # one inclusive temporal chunk of acquisiton request.
    index: int
    start: date
    end: date

    @property
    def identifier(self) -> str:
        return f"{self.start.isoformat()}_{self.end.isoformat()}"