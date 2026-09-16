from __future__ import annotations
from datetime import timedelta

from .models import AcquisitionChunk, DateRange

def build_chunks(date_range: DateRange, chunk_days: int) -> list[AcquisitionChunk]:
    # split inclusive date range into non-overlapping temporal chunks.
    if date_range.start > date_range.end:
        raise ValueError("Can't build chunks from invalid date range")
    if chunk_days <= 0:
        raise ValueError("chunk_days must be greater than 0")
    chunks: list[AcquisitionChunk] = []
    current = date_range.start
    index = 0

    while current <= date_range.end:
        chunk_end = min(current + timedelta(days=chunk_days-1), date_range.end)
        chunks.append(AcquisitionChunk(index=index, start=current, end=chunk_end))
        current = chunk_end + timedelta(days=1)
        index +=1
    return chunks