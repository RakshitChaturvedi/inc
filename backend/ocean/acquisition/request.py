from __future__ import annotations
from dataclasses import dataclass
from datetime import date

from .models import BoundingBox, DateRange

@dataclass(frozen=True)
class AcquisitionRequest:
    # user-defined req for remote data acq
    date_range: DateRange
    region: BoundingBox
    variables: tuple[str, ...]
    chunk_days: int = 7

def validate_request(request: AcquisitionRequest) -> None:
    # validate acq req before execution
    date_range = request.date_range
    region = request.region

    if date_range.start > date_range.end:
        raise ValueError("Acquisition start date cant be after end date.")
    if region.lat_min >= region.lat_max:
        raise ValueError("lat_min must be smaller than lat_max")
    if region.lon_min >= region.lon_max:
        raise ValueError("lon_min must be smaller than lon_max")
    if request.chunk_days <= 0:
        raise ValueError("chunk_days must be greater than zero.")
    if not request.variables:
        raise ValueError("At least one variable must be requested")

    for variable in request.variables:
        if not isinstance(variable, str) or not variable.strip():
            raise ValueError("All requested variables must be non-empty strings.")
        