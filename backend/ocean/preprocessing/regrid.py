from __future__ import annotations
from pathlib import Path

import numpy as np
import xarray as xr
import xesmf as xe

def create_target_grid(
        *,
        lat_min: float, lat_max: float,
        lon_min: float, lon_max: float,
        resolution: float,
) -> xr.Dataset:
    # create 0.25 grid
    latitude = np.arange(lat_min, lat_max+resolution/2, resolution)
    longitude = np.arange(lon_min, lon_max+resolution/2, resolution)

    return xr.Dataset(coords={
        "latitude": latitude,
        "longitude": longitude
    })

def create_regridder(
        ds: xr.Dataset,
        target_grid: xr.Dataset, *,
        method: str = "bilinear",
        reuse_weights: bool = True,
        weights_dir: str | Path = "data/processed/phase2/weights"
) -> xr.Dataset:
    # regrid ds 
    weights_dir = Path(weights_dir)
    weights_dir.mkdir(parents=True, exist_ok=True)

    source_name = ds.attrs.get("oceanembed_dataset", "dataset")
    weight_file = (weights_dir/f"{source_name}_{method}_weights.nc")

    if "mask" in ds:
        ds = ds.drop_vars("mask")

    regridder = xe.Regridder(
        ds, target_grid, method, filename=str(weight_file), 
        reuse_weights=reuse_weights and weight_file.exists()
    )

    return regridder

def regrid_dataset(
    ds: xr.Dataset,
    target_grid: xr.Dataset,
    *,
    method: str = "bilinear",
    reuse_weights: bool = True,
    weights_dir: str | Path = "data/processed/phase2/weights",
    regridder=None
) -> xr.Dataset:
    if "mask" in ds:
        ds = ds.drop_vars("mask")
        
    weights_dir = Path(weights_dir)
    weights_dir.mkdir(parents=True, exist_ok=True)

    source_name = ds.attrs.get("oceanembed_dataset", "dataset")
    weight_file = weights_dir / f"{source_name}_{method}_weights.nc"

    # xesmf requires 'lat' and 'lon' coordinate names
    ds_xe = ds.rename({"latitude": "lat", "longitude": "lon"})
    target_xe = target_grid.rename({"latitude": "lat", "longitude": "lon"})

    if regridder is None:
        regridder = xe.Regridder(
            ds_xe, target_xe, method, filename=str(weight_file), 
            reuse_weights=reuse_weights and weight_file.exists()
        )
        
    result = regridder(ds_xe, keep_attrs=True)
    
    # Rename back to OceanEmbed standard 'latitude' and 'longitude'
    result = result.rename({"lat": "latitude", "lon": "longitude"})
    
    result.attrs.update(ds.attrs)
    result.attrs["oceanembed_regrid_method"] = method
    result.attrs["oceanembed_grid_resolution"] = "0.25 degrees"

    return result
    