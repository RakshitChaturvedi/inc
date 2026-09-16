"""
1. coastal gaps -> spatial interpolation form neighboring valid ocean cells
2. interior cloud gaps -> spatial interpolation, preferably constrained to nearby valid ocean cells
3. large temporal gaps -> temporal interpolation using adjacent days when full time series available
4. large unresolved gaps -> flag or reject
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

import numpy as np
import xarray as xr

from scipy.ndimage import distance_transform_edt

DEFAULT_MAX_DISTANCE = 3

@dataclass
class GapFillReport:
    # diagnostics produced by gap-filling

    original_nan_counts: Dict[str, int]
    spatial_filled_counts: Dict[str, int]
    unresolved_counts: Dict[str, int]
    persistent_gap_count: int
    persistent_gap_cells: np.ndarray

def _fill_spatial_nearest(values: np.ndarray, ocean_mask: np.ndarray, max_distance: int) -> tuple[np.ndarray, int]:
    values = np.asarray(values, dtype=np.float64).copy()
    valid = np.isfinite(values) & ocean_mask
    missing = ~np.isfinite(values) & ocean_mask

    if not missing.any():
        return values, 0
    if not valid.any():
        return values, 0

    # dist from every cell to nearest valid cell
    distance, indices = distance_transform_edt(~valid, return_distances=True, return_indices=True)
    fillable = missing & (distance <= max_distance)

    if not fillable.any():
        return values, 0

    nearest_y, nearest_x = indices[0][fillable], indices[1][fillable]
    values[fillable] = values[nearest_y, nearest_x]

    return values, int(fillable.sum())

def _extract_2d(data: xr.DataArray) -> np.ndarray:
    # return 2-d lat-lon slice, used for unresolved-gap diagnostics
    values = data.values
    while values.ndim > 2:
        values = values[0]
    return values

def fill_ocean_gaps(ds: xr.Dataset, ocean_mask: np.ndarray, *, max_distance: int = DEFAULT_MAX_DISTANCE) -> xr.Dataset:
    """
    rules:
        - valid obs never changed
        - land cells never filled
        - only ocean nans are candidates
        - gaps larger than max_distance remain nan
        - raises error if unresolved ocean nans remain
    """
    if not isinstance(ocean_mask, np.ndarray):
        ocean_mask = np.asarray(ocean_mask)
    if ocean_mask.dtype != bool:
        ocean_mask = ocean_mask.astype(bool)

    expected_shape = (ds.sizes["latitude"], ds.sizes["longitude"])
    if ocean_mask.shape != expected_shape:
        raise ValueError(f"Ocean mask shape doesnt match ds grid: mask={ocean_mask.shape}, grid={expected_shape}")
    if max_distance < 1:
        raise ValueError("max_distance must be >= 1")
    
    result = ds.copy()
    original_nan_counts: Dict[str, int] = {}
    spatial_filled_counts: Dict[str, int] = {}
    unresolved_counts: Dict[str, int] = {}
    persistent_gap_mask = np.zeros_like(ocean_mask, dtype=bool)

    for variable in result.data_vars:
        data = result[variable]
        if "latitude" not in data.dims or "longitude" not in data.dims:
            continue

        spatial_shape = (data.sizes["latitude"], data.sizes["longitude"])
        if spatial_shape != ocean_mask.shape:
            raise ValueError(f"{variable}: spatial shape {spatial_shape} doesnt match ocean mask {ocean_mask.shape}")

        spatial_dims = ("latitude", "longitude")
        other_dims = [dim for dim in data.dims if dim not in spatial_dims]
        if not other_dims:
            arrays = [data.values]
        else:
            arrays = data.values.reshape((-1, data.sizes["latitude"], data.sizes["longitude"]))

        total_original_nan = 0
        total_filled = 0
        filled_arrays = []

        for array in arrays:
            ocean_nan = (np.isnan(array) & ocean_mask)
            total_original_nan += int(ocean_nan.sum())

            filled, count = _fill_spatial_nearest(array, ocean_mask, max_distance)
            filled_arrays.append(filled)
            total_filled+=count

        if not other_dims:
            new_values = filled_arrays[0]
        else:
            new_values = np.stack(filled_arrays, axis=0)
            new_values = new_values.reshape(data.shape)
        result[variable] = xr.DataArray(
            new_values,
            dims=data.dims,
            coords=data.coords,
            attrs=data.attrs,
            name=data.name,
        )

        original_nan_counts[variable] = (total_original_nan)
        spatial_filled_counts[variable] = (total_filled)
        remaining_values = _extract_2d(result[variable])
        remaining = (np.isnan(remaining_values) & ocean_mask)
        remaining_count = int(remaining.sum())
        unresolved_counts[variable] = (remaining_count)

        if total_filled:
            print(f"Gap filling: {variable}: filled {total_filled} ocean cells")

        if remaining_count:
            print(f"Gap filling: {variable}: {remaining_count} unresolved ocean cells")
            persistent_gap_mask |= remaining

    # building computational mask
    effective_ocean_mask = (ocean_mask & ~persistent_gap_mask)
    persistent_gap_cells = np.argwhere(persistent_gap_mask)
    report = GapFillReport(
        original_nan_counts=original_nan_counts,
        spatial_filled_counts=spatial_filled_counts,
        unresolved_counts=unresolved_counts,
        persistent_gap_count=int(persistent_gap_mask.sum()),
        persistent_gap_cells=persistent_gap_cells,
    )

    print()
    print("=" * 70)
    print("GAP FILLING SUMMARY")
    print("=" * 70)
    for variable in original_nan_counts:
        print(
            f"{variable:20s} original NaNs = {original_nan_counts[variable]:6d} | "
            f"spatial filled = {spatial_filled_counts[variable]:6d} | "
            f"unresolved = {unresolved_counts[variable]:6d}"
        )
    print()
    print(f"Persistent unresolved cells : {report.persistent_gap_count}")
    print(f"Original ocean cells        : {int(ocean_mask.sum())}")
    print(f"Effective ocean cells       : {int(effective_ocean_mask.sum())}")

    if report.persistent_gap_count:
        print()
        print("Persistent unresolved cells:")
        for y, x in persistent_gap_cells:
            lat = float(ds.latitude.values[y])
            lon = float(ds.longitude.values[x])

            print(f"  ({lat:.2f}, {lon:.2f})")
    print()

    return (result, effective_ocean_mask, report)