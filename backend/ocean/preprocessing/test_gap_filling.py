from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path
from scipy.ndimage import distance_transform_edt

from ocean.preprocessing.schema import open_standardized
from ocean.preprocessing.harmonize import (
    harmonize_sst,
    harmonize_sss,
    harmonize_ssh,
    harmonize_currents,
)
from ocean.preprocessing.temporal import align_daily
from ocean.preprocessing.spatial import subset_domain
from ocean.preprocessing.regrid import create_target_grid, regrid_dataset

warnings.filterwarnings("ignore", message="Input array is not C_CONTIGUOUS")

ROOT = Path("data/raw/a12_test/2025-01-01_2025-01-07")
REGISTRY = Path("model-registry/oceanembed-v1.0.0/ocean_mask.nc")

DOMAIN = {
    "lat_min": 5.0,
    "lat_max": 30.0,
    "lon_min": 45.0,
    "lon_max": 105.0,
}


def get_paths():
    return {
        "sst": next((ROOT / "sst").glob("*.nc")),
        "sss": next((ROOT / "sss").glob("*.nc")),
        "ssh": next((ROOT / "ssh").glob("*.nc")),
        "currents": next((ROOT / "currents").glob("*.nc")),
    }


def prepare_dataset(name, path, date):
    if name == "sst":
        ds = harmonize_sst(
            open_standardized(path, dataset_name="SST")
        )

    elif name == "sss":
        ds = harmonize_sss(
            open_standardized(path, dataset_name="SSS")
        )

        if "depth" in ds.dims:
            ds = ds.isel(depth=0, drop=True)

    elif name == "ssh":
        ds = harmonize_ssh(
            open_standardized(path, dataset_name="SSH")
        )

    elif name == "currents":
        ds = harmonize_currents(
            open_standardized(path, dataset_name="CURRENTS")
        )

        if "depth" in ds.dims:
            ds = ds.isel(depth=0, drop=True)

    else:
        raise ValueError(name)

    return align_daily(ds, start=date, end=date)


def find_remaining_cells(values, ocean_mask, max_distance=3):
    valid = np.isfinite(values) & ocean_mask
    missing = np.isnan(values) & ocean_mask

    if not missing.any():
        return np.empty((0, 2), dtype=int)

    distance, _ = distance_transform_edt(
        ~valid,
        return_distances=True,
        return_indices=True,
    )

    remaining = missing & (distance > max_distance)

    return np.argwhere(remaining)


def main():
    target_grid = create_target_grid(
        **DOMAIN,
        resolution=0.25,
    )

    with xr.open_dataset(REGISTRY) as mask_ds:
        ocean_mask = mask_ds["ocean_mask"].values.astype(bool)
        target_lat = mask_ds["latitude"].values
        target_lon = mask_ds["longitude"].values

    paths = get_paths()

    # ----------------------------------------------------------
    # Step 1: Find unresolved cells on 2025-01-02
    # ----------------------------------------------------------

    reference_date = "2025-01-02"

    print("=" * 70)
    print(f"FINDING >3-CELL GAPS ON {reference_date}")
    print("=" * 70)

    remaining_cells = {}

    for name in paths:
        ds = prepare_dataset(name, paths[name], reference_date)

        regridded = regrid_dataset(
            subset_domain(ds, **DOMAIN),
            target_grid,
        )

        for variable in regridded.data_vars:
            values = regridded[variable].values.squeeze()

            cells = find_remaining_cells(
                values,
                ocean_mask,
                max_distance=3,
            )

            if len(cells):
                remaining_cells[variable] = cells

                print(
                    f"\n{variable}: {len(cells)} unresolved cells"
                )

                for y, x in cells:
                    print(
                        f"  ({target_lat[y]:.2f}, "
                        f"{target_lon[x]:.2f})"
                    )

    if not remaining_cells:
        print("\nNo >3-cell gaps found.")
        return

    # ----------------------------------------------------------
    # Step 2: Check the SAME cells on every day
    # ----------------------------------------------------------

    print()
    print("=" * 70)
    print("TEMPORAL AVAILABILITY OF SAME CELLS")
    print("=" * 70)

    dates = pd.date_range(
        "2025-01-01",
        "2025-01-07",
        freq="1D",
    )

    for variable, cells in remaining_cells.items():

        print()
        print("-" * 70)
        print(variable)
        print("-" * 70)

        name = (
            "currents"
            if variable in ("current_u", "current_v")
            else variable
        )

        for y, x in cells:
            lat = target_lat[y]
            lon = target_lon[x]

            status = []

            for date in dates:
                date_str = date.strftime("%Y-%m-%d")

                ds = prepare_dataset(
                    name,
                    paths[name],
                    date_str,
                )

                regridded = regrid_dataset(
                    subset_domain(ds, **DOMAIN),
                    target_grid,
                )

                value = regridded[variable].values.squeeze()[y, x]

                status.append(
                    "VALID"
                    if np.isfinite(value)
                    else "NaN"
                )

            print(
                f"({lat:.2f}, {lon:.2f}) : "
                + " | ".join(status)
            )


if __name__ == "__main__":
    main()