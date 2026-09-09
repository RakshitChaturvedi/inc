from __future__ import annotations
import xarray as xr

def subset_domain(
        ds: xr.Dataset,
        *,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float
) -> xr.Dataset:
    # subset a ds to oceanembed domain

    if "latitude" not in ds.coords:
        raise ValueError("Dataset has no 'latitude' coordinate.")

    if "longitude" not in ds.coords:
        raise ValueError("Dataset has no 'longitude' coordinate.")

    ds = ds.sortby("latitude")
    ds = ds.sortby("longitude")

    # Validate overlap before slicing.
    dataset_lat_min = float(ds.latitude.min())
    dataset_lat_max = float(ds.latitude.max())
    dataset_lon_min = float(ds.longitude.min())
    dataset_lon_max = float(ds.longitude.max())

    if (
        lat_max < dataset_lat_min
        or lat_min > dataset_lat_max
        or lon_max < dataset_lon_min
        or lon_min > dataset_lon_max
    ):
        raise ValueError(
            "Requested domain does not overlap dataset domain. "
            f"Dataset: "
            f"{dataset_lat_min}..{dataset_lat_max} latitude, "
            f"{dataset_lon_min}..{dataset_lon_max} longitude. "
            f"Requested: "
            f"{lat_min}..{lat_max}, "
            f"{lon_min}..{lon_max}."
        )

    ds = ds.sel(
        latitude=slice(lat_min, lat_max),
        longitude=slice(lon_min, lon_max),
    )

    if ds.sizes.get("latitude", 0) == 0:
        raise ValueError("Latitude subset produced zero points.")

    if ds.sizes.get("longitude", 0) == 0:
        raise ValueError("Longitude subset produced zero points.")

    return ds