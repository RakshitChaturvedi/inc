from __future__ import annotations
from pathlib import Path
from typing import Iterable

import numpy as np
import xarray as xr

COMMON_COORDS = {
    "lat": "latitude",
    "lon": "longitude",
    "latitude": "latitude",
    "longitude": "longitude",
}

def _rename_first_existing(
        ds: xr.Dataset,
        candidates: list[str],
        target: str,
) -> xr.Dataset:
    if target in ds.coords:
        return ds

    for name in candidates:
        if name in ds.coords:
            if name != target:
                ds = ds.rename({name: target})
            return ds
    raise ValueError(
        f"Could not find coordinate for '{target}'. "
        f"Available coordinates: {list(ds.coords)}"
    )

def standardize_coordinates(ds: xr.Dataset) -> xr.Dataset:
    # normalize lat long names and ensure latitude is ascending
    ds = _rename_first_existing(ds, target="latitude",candidates= ["lat", "nav_lat", "y"])
    ds = _rename_first_existing(ds, target="longitude", candidates=["lon", "nav_lon", "x"])

    if "latitude" in ds.coords:
        ds = ds.swap_dims({
            next(dim for dim in ds.dims if dim in ds["latitude"].dims): "latitude"
        })

    if "longitude" in ds.coords:
        ds = ds.swap_dims({
            next(dim for dim in ds.dims if dim in ds["longitude"].dims): "longitude"
        })

    lon = ds["longitude"]
    if float(lon.max()) > 180:
        normalized_lon = ((lon+180)%360) - 180
        ds = ds.assign_coords(longitude=normalized_lon)
        ds = ds.sortby("longitude")

    return ds

def standardize_time(ds: xr.Dataset) -> xr.Dataset:
    # normalize time coordinate to useful datetime64. 

    if "time" not in ds.coords:
        raise ValueError("Dataset has no time coords.")
    time = ds["time"]

    if np.issubdtype(time.dtype, np.datetime64): return ds

    try:
        ds = ds.convert_calendar("standard", use_cftime=False) 
    except Exception as exc:
        try:
            values = [np.datetime64(str(value)) for value in time.values]
            ds = ds.assign_coords(time=("time", values))
        except Exception as fallback_e:
            raise ValueError(
                "Couldnt convert ds time coord to numpy datetime64."
                f"Original error: {exc}, Fallback error: {fallback_e}"
            )
    if not np.issubdtype(ds["time"].dtype, np.datetime64):
        raise TypeError(f"Time standardization failed. Got dtype: {ds['time'].dtype}")

    return ds

def standardize_dataset(ds: xr.Dataset, *, dataset_name: str) -> xr.Dataset:
    # apply common schema normalization
    ds = standardize_coordinates(ds)
    ds = standardize_time(ds)
    ds = ds.sortby("time")

    _, unique_indices = np.unique(ds["time"].values, return_index=True)
    if len(unique_indices) != ds.sizes["time"]:
        ds = ds.isel(time=np.sort(unique_indices))

    ds.attrs["oceanembed_dataset"] = dataset_name
    ds.attrs["oceanembed_schema_version"] = "phase2-v1"

    return ds

def open_standardized(path: str | Path, *, dataset_name: str) -> xr.Dataset:
    # open netcdf dataset lazily and standardize its corods

    print(f"Opening: {path}")
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    ds = xr.open_dataset(path, decode_times=True)
    ds=standardize_dataset(ds, dataset_name=dataset_name)

    return ds
    