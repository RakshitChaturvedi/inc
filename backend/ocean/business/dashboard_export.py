from __future__ import annotations

from pathlib import Path
from typing import Mapping

import numpy as np
import xarray as xr


# ---------------------------------------------------------------------------
# Dashboard Contract
# ---------------------------------------------------------------------------

REQUIRED_BASE_VARIABLES = (
    "temperature_mean",
    "salinity_mean",
    "temperature_std",
    "salinity_std",
)

REQUIRED_BUSINESS_VARIABLES = (
    "tchp",
    "d26",
    "mld",
    "thermocline_depth",
)

REQUIRED_DIMENSIONS = (
    "time",
    "depth",
    "latitude",
    "longitude",
)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_base_dataset(ds: xr.Dataset) -> None:
    """
    Validate the physics-adjusted dataset before dashboard assembly.

    Raises
    ------
    ValueError
        If required dimensions, coordinates, or variables are missing.
    """

    missing_dims = [
        dim for dim in REQUIRED_DIMENSIONS
        if dim not in ds.dims
    ]

    if missing_dims:
        raise ValueError(
            f"Base dataset missing required dimensions: {missing_dims}"
        )

    missing_vars = [
        var for var in REQUIRED_BASE_VARIABLES
        if var not in ds.data_vars
    ]

    if missing_vars:
        raise ValueError(
            f"Base dataset missing required variables: {missing_vars}"
        )

    expected_shape = (
        ds.sizes["time"],
        ds.sizes["depth"],
        ds.sizes["latitude"],
        ds.sizes["longitude"],
    )

    for variable in REQUIRED_BASE_VARIABLES:
        actual_shape = ds[variable].transpose(
            "time",
            "depth",
            "latitude",
            "longitude",
        ).shape

        if actual_shape != expected_shape:
            raise ValueError(
                f"{variable} has incompatible shape: "
                f"{actual_shape}; expected {expected_shape}"
            )


def validate_business_variables(
    business_variables: Mapping[str, xr.DataArray],
    ds: xr.Dataset,
) -> None:
    """
    Validate derived business variables before insertion into the dashboard
    dataset.
    """

    missing = [
        name
        for name in REQUIRED_BUSINESS_VARIABLES
        if name not in business_variables
    ]

    if missing:
        raise ValueError(
            f"Missing required business variables: {missing}"
        )

    spatial_dims = (
        "time",
        "latitude",
        "longitude",
    )

    for name in REQUIRED_BUSINESS_VARIABLES:
        da = business_variables[name]

        missing_dims = [
            dim for dim in spatial_dims
            if dim not in da.dims
        ]

        if missing_dims:
            raise ValueError(
                f"{name} is missing required dimensions: {missing_dims}"
            )

        # Business variables should not retain an unnecessary depth
        # dimension in the final dashboard representation.
        unexpected_dims = [
            dim for dim in da.dims
            if dim not in spatial_dims
        ]

        if unexpected_dims:
            raise ValueError(
                f"{name} contains unexpected dimensions: "
                f"{unexpected_dims}"
            )

        expected_shape = tuple(
            ds.sizes[dim] for dim in spatial_dims
        )

        actual_shape = da.transpose(*spatial_dims).shape

        if actual_shape != expected_shape:
            raise ValueError(
                f"{name} has incompatible shape: "
                f"{actual_shape}; expected {expected_shape}"
            )


# ---------------------------------------------------------------------------
# Dashboard Dataset Construction
# ---------------------------------------------------------------------------

def build_dashboard_dataset(
    physics_ds: xr.Dataset,
    business_variables: Mapping[str, xr.DataArray],
) -> xr.Dataset:
    """
    Construct the final dashboard-facing Dataset.

    Parameters
    ----------
    physics_ds:
        Physics-adjusted dataset containing the ensemble mean/std fields.

    business_variables:
        Mapping containing:
            - tchp
            - mld
            - thermocline_depth

    Returns
    -------
    xr.Dataset
        Dashboard-ready dataset.
    """

    validate_base_dataset(physics_ds)
    validate_business_variables(
        business_variables,
        physics_ds,
    )

    # ------------------------------------------------------------------
    # Preserve the core prediction products
    # ------------------------------------------------------------------

    dashboard = xr.Dataset(
        {
            "temperature_mean": physics_ds[
                "temperature_mean"
            ].transpose(
                "time",
                "depth",
                "latitude",
                "longitude",
            ),

            "salinity_mean": physics_ds[
                "salinity_mean"
            ].transpose(
                "time",
                "depth",
                "latitude",
                "longitude",
            ),

            "temperature_std": physics_ds[
                "temperature_std"
            ].transpose(
                "time",
                "depth",
                "latitude",
                "longitude",
            ),

            "salinity_std": physics_ds[
                "salinity_std"
            ].transpose(
                "time",
                "depth",
                "latitude",
                "longitude",
            ),

            "tchp": business_variables[
                "tchp"
            ].transpose(
                "time",
                "latitude",
                "longitude",
            ),

            "mld": business_variables[
                "mld"
            ].transpose(
                "time",
                "latitude",
                "longitude",
            ),

            "thermocline_depth": business_variables[
                "thermocline_depth"
            ].transpose(
                "time",
                "latitude",
                "longitude",
            ),
        },
        coords={
            "time": physics_ds["time"],
            "depth": physics_ds["depth"],
            "latitude": physics_ds["latitude"],
            "longitude": physics_ds["longitude"],
        },
    )

    # ------------------------------------------------------------------
    # Variable Metadata
    # ------------------------------------------------------------------

    dashboard["temperature_mean"].attrs.update(
        {
            "long_name": "Physics-adjusted ensemble mean temperature",
            "units": "degC",
            "description": (
                "Ensemble mean temperature after convective adjustment."
            ),
        }
    )

    dashboard["salinity_mean"].attrs.update(
        {
            "long_name": "Physics-adjusted ensemble mean salinity",
            "units": "psu",
            "description": (
                "Ensemble mean salinity after convective adjustment."
            ),
        }
    )

    dashboard["temperature_std"].attrs.update(
        {
            "long_name": "Temperature ensemble standard deviation",
            "units": "degC",
            "description": (
                "Ensemble spread of physics-adjusted temperature."
            ),
        }
    )

    dashboard["salinity_std"].attrs.update(
        {
            "long_name": "Salinity ensemble standard deviation",
            "units": "psu",
            "description": (
                "Ensemble spread of physics-adjusted salinity."
            ),
        }
    )

    dashboard["tchp"].attrs.update(
        {
            "long_name": "Tropical Cyclone Heat Potential",
            "units": "kJ cm-2",
            "description": (
                "Integrated upper-ocean heat content relevant to "
                "tropical cyclone intensity."
            ),
        }
    )

    dashboard["mld"].attrs.update(
        {
            "long_name": "Mixed Layer Depth",
            "units": "m",
            "description": "Estimated depth of the ocean mixed layer.",
        }
    )

    dashboard["thermocline_depth"].attrs.update(
        {
            "long_name": "Thermocline Depth",
            "units": "m",
            "description": "Estimated depth of the thermocline.",
        }
    )

    # ------------------------------------------------------------------
    # Dataset Metadata
    # ------------------------------------------------------------------

    dashboard.attrs.update(
        {
            "project": "OceanEmbed",
            "artifact": "dashboard_ready",
            "product": "OceanEmbed operational dashboard dataset",
            "source_artifact": "physics_adjusted.nc",
            "business_layer": "tchp,d26,mld,thermocline",
            "convective_adjustment": "applied",
            "schema_version": "1.0",
        }
    )

    return dashboard


# ---------------------------------------------------------------------------
# Final Validation
# ---------------------------------------------------------------------------

def validate_dashboard_dataset(ds: xr.Dataset) -> None:
    """
    Validate the final dashboard dataset.

    This is intended to be called immediately before export.
    """

    required_variables = (
        *REQUIRED_BASE_VARIABLES,
        *REQUIRED_BUSINESS_VARIABLES,
    )

    missing = [
        variable
        for variable in required_variables
        if variable not in ds.data_vars
    ]

    if missing:
        raise ValueError(
            f"Dashboard dataset missing variables: {missing}"
        )

    required_dims = (
        "time",
        "depth",
        "latitude",
        "longitude",
    )

    missing_dims = [
        dim
        for dim in required_dims
        if dim not in ds.dims
    ]

    if missing_dims:
        raise ValueError(
            f"Dashboard dataset missing dimensions: {missing_dims}"
        )

    # Ensure all core 4-D fields are finite where data exists.
    for variable in REQUIRED_BASE_VARIABLES:
        values = ds[variable].values

        if not np.issubdtype(values.dtype, np.number):
            raise ValueError(
                f"{variable} is not numeric."
            )

    # Business variables must be 3-D.
    for variable in REQUIRED_BUSINESS_VARIABLES:
        dims = ds[variable].dims

        if dims != ("time", "latitude", "longitude"):
            raise ValueError(
                f"{variable} has invalid dimensions: {dims}"
            )

    # Coordinate consistency.
    for dim in required_dims:
        if dim not in ds.coords:
            raise ValueError(
                f"Missing coordinate for dimension '{dim}'."
            )

    if ds.sizes["time"] == 0:
        raise ValueError("Dashboard dataset contains no time steps.")

    if ds.sizes["latitude"] == 0 or ds.sizes["longitude"] == 0:
        raise ValueError("Dashboard dataset contains an empty spatial grid.")


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_dashboard_dataset(
    ds: xr.Dataset,
    output_path: str | Path,
    *,
    compression: bool = True,
) -> Path:
    """
    Validate and write the final dashboard dataset to NetCDF.
    """

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    validate_dashboard_dataset(ds)

    encoding = {}

    if compression:
        for variable in ds.data_vars:
            encoding[variable] = {
                "zlib": True,
                "complevel": 4,
                "dtype": "float32",
            }

    ds.to_netcdf(
        output_path,
        engine="netcdf4",
        encoding=encoding,
        unlimited_dims=["time"],
    )

    return output_path


# ---------------------------------------------------------------------------
# Inspection Helper
# ---------------------------------------------------------------------------

def inspect_dashboard_dataset(
    ds: xr.Dataset,
) -> dict:
    """
    Return a lightweight summary suitable for logging or tests.
    """

    validate_dashboard_dataset(ds)

    return {
        "dimensions": {
            dim: int(size)
            for dim, size in ds.sizes.items()
        },
        "variables": list(ds.data_vars),
        "time_start": str(ds.time.values[0]),
        "time_end": str(ds.time.values[-1]),
        "depths": ds.depth.values.tolist(),
        "latitude_range": [
            float(ds.latitude.values.min()),
            float(ds.latitude.values.max()),
        ],
        "longitude_range": [
            float(ds.longitude.values.min()),
            float(ds.longitude.values.max()),
        ],
        "schema_version": ds.attrs.get(
            "schema_version",
            "unknown",
        ),
    }