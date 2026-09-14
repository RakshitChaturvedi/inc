from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

EARTH_RADIUS = 6_371_000.0
AIR_DENSITY = 1.225
DRAG_COEFFICIENT = 1.3e-3

def compute_drag_coefficient(wind_speed: xr.DataArray) -> xr.DataArray:
    return xr.full_like(wind_speed, DRAG_COEFFICIENT)

def compute_wind_stress(wind_u: xr.DataArray, wind_v: xr.DataArray, wind_speed: xr.DataArray) -> tuple[xr.DataArray, xr.DataArray]:
    # compute surface wind-stress components (Units: N/m^2)
    # tau_x = rho_air * Cd * |U| * U
    # tau_y = rho_air * Cd * |U| * V

    cd = compute_drag_coefficient(wind_speed)
    tau_x = AIR_DENSITY*cd*wind_speed*wind_u
    tau_y = AIR_DENSITY*cd*wind_speed*wind_v

    tau_x.attrs.update({
        "long_name": "zonal wind stress",
        "units": "N m-2",  
        "air_density": AIR_DENSITY,
        "drag_coefficient": DRAG_COEFFICIENT
    })

    tau_y.attrs.update({
        "long_name": "meridonal wind stress",
        "units": "N m-2",  
        "air_density": AIR_DENSITY,
        "drag_coefficient": DRAG_COEFFICIENT
    })

    return tau_x, tau_y

def compute_wind_stress_curl(tau_x: xr.DataArray, tau_y: xr.DataArray) -> xr.Dataset:
    """
    curl_tau = d(tau_y)/dx - d(tau_x)/dy
    derivatives cal wrt lat/lon and converted to physical spherical-earth dist.
    """
    lat_rad = np.deg2rad(tau_x["latitude"])
    deg2rad = 180.0/np.pi

    d_tau_y_dlon = tau_y.differentiate("longitude")
    d_tau_x_dlat = tau_x.differentiate("latitude")

    d_tau_y_dlambda = d_tau_x_dlat * deg2rad
    d_tau_x_dphi = d_tau_x_dlat * deg2rad
    cos_lat = np.cos(lat_rad)

    # spehrical earth. dx=R*cos(phi)*d(lambda), dy=R*d(phi)
    d_tau_y_dx = d_tau_y_dlambda/(EARTH_RADIUS*cos_lat)
    d_tau_x_dy = d_tau_x_dphi/EARTH_RADIUS

    curl = d_tau_y_dx - d_tau_x_dy
    curl.name = "wind_stress_curl"

    curl.attrs.update({
        "long_name": "curl of surface wind stress",
        "standard_name": "wind_stress_curl",
        "units": "N m-3",
        "formula": "d(tau_y)/dx - d(tau_x)/dy",
        "earth_radius_m": EARTH_RADIUS,
        "numerical_differentiation": "xarray.differentiate",
        "interior_difference": "centered",
        "boundary_difference": "one-sided",
    })

    return curl

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