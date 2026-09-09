from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from .common import existing_dates, missing_ranges


def download_collection(
    *,
    collection: str,
    output_dir: str,
    start_date: str,
    end_date: str,
    bbox: dict,
) -> None:

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    existing = existing_dates(output)

    print(f"\n=== PO.DAAC: {collection} ===")
    print(f"Existing dates detected: {len(existing)}")

    ranges = missing_ranges(
        start,
        end,
        existing,
    )

    if not ranges:
        print("Everything already downloaded.")
        return

    for rstart, rend in ranges:

        command = [
            "podaac-data-downloader",
            "-c",
            collection,
            "-d",
            str(output),
            "--start-date",
            f"{rstart}T00:00:00Z",
            "--end-date",
            f"{rend}T23:59:59Z",
            (
                f"-b={bbox['lon_min']},{bbox['lat_min']},"
                f"{bbox['lon_max']},{bbox['lat_max']}"
            ),
        ]

        print("\n$", " ".join(command))

        subprocess.run(
            command,
            check=True,
        )


def acquire_podaac(cfg: dict) -> None:

    sources = cfg["podaac"]
    bbox = cfg["domain"]

    for name in (
        "sst",
        "sss",
        "wind",
        "currents",
    ):

        source = sources[name]

        if not source.get("enabled", True):
            print(f"Skipping {name}: disabled.")
            continue

        download_collection(
            collection=source["collection"],
            output_dir=source["output_dir"],
            start_date=cfg["dates"]["start"],
            end_date=cfg["dates"]["end"],
            bbox=bbox,
        )