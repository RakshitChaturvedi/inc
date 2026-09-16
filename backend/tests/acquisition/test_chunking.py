from datetime import date, timedelta

import pytest

from ocean.acquisition.chunking import build_chunks
from ocean.acquisition.models import DateRange


def test_one_week_produces_one_chunk():
    date_range = DateRange(
        start=date(2025, 1, 1),
        end=date(2025, 1, 7),
    )

    chunks = build_chunks(date_range, 7)

    assert len(chunks) == 1

    assert chunks[0].index == 0
    assert chunks[0].start == date(2025, 1, 1)
    assert chunks[0].end == date(2025, 1, 7)


def test_ten_days_produces_two_chunks():
    date_range = DateRange(
        start=date(2025, 1, 1),
        end=date(2025, 1, 10),
    )

    chunks = build_chunks(date_range, 7)

    assert len(chunks) == 2

    assert chunks[0].start == date(2025, 1, 1)
    assert chunks[0].end == date(2025, 1, 7)

    assert chunks[1].start == date(2025, 1, 8)
    assert chunks[1].end == date(2025, 1, 10)


def test_month_is_split_correctly():
    date_range = DateRange(
        start=date(2025, 1, 1),
        end=date(2025, 1, 31),
    )

    chunks = build_chunks(date_range, 7)

    assert len(chunks) == 5

    expected = [
        (date(2025, 1, 1), date(2025, 1, 7)),
        (date(2025, 1, 8), date(2025, 1, 14)),
        (date(2025, 1, 15), date(2025, 1, 21)),
        (date(2025, 1, 22), date(2025, 1, 28)),
        (date(2025, 1, 29), date(2025, 1, 31)),
    ]

    actual = [
        (chunk.start, chunk.end)
        for chunk in chunks
    ]

    assert actual == expected


def test_chunk_indices_are_sequential():
    date_range = DateRange(
        start=date(2025, 1, 1),
        end=date(2025, 1, 31),
    )

    chunks = build_chunks(date_range, 7)

    assert [chunk.index for chunk in chunks] == [
        0, 1, 2, 3, 4
    ]


def test_chunks_have_no_gaps_or_overlaps():
    date_range = DateRange(
        start=date(2025, 1, 1),
        end=date(2025, 1, 31),
    )

    chunks = build_chunks(date_range, 7)

    for previous, current in zip(chunks, chunks[1:]):
        assert current.start == (
            previous.end + timedelta(days=1)
        )

def test_single_day_range():
    date_range = DateRange(
        start=date(2025, 1, 15),
        end=date(2025, 1, 15),
    )

    chunks = build_chunks(date_range, 7)

    assert len(chunks) == 1
    assert chunks[0].start == date(2025, 1, 15)
    assert chunks[0].end == date(2025, 1, 15)


def test_invalid_range():
    date_range = DateRange(
        start=date(2025, 1, 10),
        end=date(2025, 1, 1),
    )

    with pytest.raises(ValueError, match="invalid date range"):
        build_chunks(date_range, 7)

def test_chunk_identifier():
    date_range = DateRange(
        start=date(2025, 1, 1),
        end=date(2025, 1, 7),
    )

    chunks = build_chunks(date_range, 7)

    assert chunks[0].identifier == "2025-01-01_2025-01-07"

def test_invalid_chunk_size():
    date_range = DateRange(
        start=date(2025, 1, 1),
        end=date(2025, 1, 7),
    )

    with pytest.raises(ValueError, match="chunk_days"):
        build_chunks(date_range, 0)