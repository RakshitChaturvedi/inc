from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

def compute_wind_stress_curl(ds: xr.Dataset) -> xr.Dataset:
    """
    Computes wind stress curl using central finite differences.
    Assumes wind_U and wind_V are present in the dataset.
    """
    if "wind_u" not in ds.data_vars or "wind_v" not in ds.data_vars:
        raise ValueError("wind_U and wind_V required for wind stress curl.")

    # Earth radius in meters
    R = 6371000.0 
    
    # Convert lat/lon spacing to radians
    lon_rad = np.deg2rad(ds.longitude)
    lat_rad = np.deg2rad(ds.latitude)
    
    # Calculate grid spacing in meters (dx depends on latitude, dy is constant)
    dx = R * np.cos(lat_rad) * float(lon_rad.diff("longitude").mean())
    dy = R * float(lat_rad.diff("latitude").mean())
    
    # Central difference derivatives: dV/dx - dU/dy
    dv_dx = ds["wind_v"].differentiate("longitude") / dx
    du_dy = ds["wind_u"].differentiate("latitude") / dy
    
    # Standard pseudo-stress curl approximation
    ds["wind_stress_curl"] = dv_dx - du_dy
    ds["wind_stress_curl"].attrs["units"] = "N m-3"
    
    return ds

def add_spatial_features(ds: xr.Dataset) -> xr.Dataset:
    """
    Broadcasts the 1D latitude and longitude coordinates into 2D data variables.
    """
    lon_2d, lat_2d = np.meshgrid(ds.longitude.values, ds.latitude.values)
    
    # Using '_var' suffix temporarily so xarray doesn't confuse them with coords
    ds["latitude_var"] = (("latitude", "longitude"), lat_2d)
    ds["longitude_var"] = (("latitude", "longitude"), lon_2d)
    
    return ds

def add_temporal_features(ds: xr.Dataset) -> xr.Dataset:
    """
    Generates sin and cos of the day of the year.
    """
    if "time" not in ds.coords:
        raise ValueError("Dataset missing 'time' coordinate.")

    time_dt = pd.DatetimeIndex(ds.time.values)
    day_of_year = time_dt.dayofyear.values
    
    # Broadcast scalar day of year to full spatial grid
    sin_doy = np.sin(2 * np.pi * day_of_year / 365.25)
    cos_doy = np.cos(2 * np.pi * day_of_year / 365.25)
    
    shape = (len(time_dt), ds.sizes["latitude"], ds.sizes["longitude"])
    
    ds["sin_day_of_year"] = (
        ("time", "latitude", "longitude"), 
        sin_doy[:, None, None] * np.ones(shape)
    )
    
    ds["cos_day_of_year"] = (
        ("time", "latitude", "longitude"), 
        cos_doy[:, None, None] * np.ones(shape)
    )
    
    return ds