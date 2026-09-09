from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_DEPTHS = np.array(
    [
        0.0,
        5.0,
        10.0,
        20.0,
        30.0,
        50.0,
        75.0,
        100.0,
        125.0,
        150.0,
        200.0,
        300.0,
        500.0,
        700.0,
        1000.0,
    ],
    dtype=np.float32,
)


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

def calculate_thermocline_depth(
    temperature: np.ndarray,
    depths: np.ndarray,
    min_valid_levels: int = 3,
) -> np.ndarray:
    """
    Calculate thermocline depth as the depth of maximum absolute
    vertical temperature gradient.

    Parameters
    ----------
    temperature:
        Temperature array with shape (..., depth).

    depths:
        1-D depth coordinate with shape (depth,).

    min_valid_levels:
        Minimum number of finite temperature levels required for a
        thermocline estimate.

    Returns
    -------
    np.ndarray
        Thermocline depth with shape (...).

    Notes
    -----
    The gradient is calculated between adjacent valid depth levels:

        |T[i+1] - T[i]| / |z[i+1] - z[i]|

    The returned thermocline depth is the midpoint of the two depths
    surrounding the maximum gradient.
    """

    temperature = np.asarray(temperature, dtype=np.float32)
    depths = np.asarray(depths, dtype=np.float32)

    if temperature.ndim < 1:
        raise ValueError("temperature must have at least one dimension.")

    if depths.ndim != 1:
        raise ValueError("depths must be a 1-D array.")

    if temperature.shape[-1] != len(depths):
        raise ValueError(
            "Depth dimension mismatch: "
            f"temperature has {temperature.shape[-1]} levels, "
            f"but depths has {len(depths)}."
        )

    if len(depths) < 2:
        raise ValueError("At least two depth levels are required.")

    if np.any(~np.isfinite(depths)):
        raise ValueError("Depth coordinates must be finite.")

    if np.any(np.diff(depths) <= 0):
        raise ValueError("Depth coordinates must be strictly increasing.")

    valid_level_count = np.sum(np.isfinite(temperature), axis=-1)

    # Gradient between adjacent depth levels.
    dz = np.diff(depths)

    t_upper = temperature[..., :-1]
    t_lower = temperature[..., 1:]

    valid_pairs = np.isfinite(t_upper) & np.isfinite(t_lower)

    gradient = np.full(
        temperature.shape[:-1] + (len(depths) - 1,),
        np.nan,
        dtype=np.float32,
    )

    np.divide(
        np.abs(t_lower - t_upper),
        dz,
        out=gradient,
        where=valid_pairs,
    )

    # Columns with insufficient valid observations cannot produce
    # a meaningful thermocline estimate.
    sufficient_data = valid_level_count >= min_valid_levels

    has_gradient = np.any(np.isfinite(gradient), axis=-1)
    valid_columns = sufficient_data & has_gradient

    # NaNs cannot safely participate in argmax.
    gradient_for_argmax = np.where(
        np.isfinite(gradient),
        gradient,
        -np.inf,
    )

    max_gradient_index = np.argmax(
        gradient_for_argmax,
        axis=-1,
    )

    # Thermocline is assigned to the midpoint of the depth interval
    # containing the strongest temperature gradient.
    depth_upper = depths[max_gradient_index]
    depth_lower = depths[max_gradient_index + 1]

    thermocline_depth = (depth_upper + depth_lower) / 2.0

    thermocline_depth = np.where(
        valid_columns,
        thermocline_depth,
        np.nan,
    ).astype(np.float32)

    return thermocline_depth


# ---------------------------------------------------------------------------
# Xarray wrapper
# ---------------------------------------------------------------------------

def calculate_thermocline(
    temperature: xr.DataArray,
    depth_dim: str = "depth",
    min_valid_levels: int = 3,
) -> xr.DataArray:
    """
    Calculate thermocline depth from an xarray temperature DataArray.

    Expected input dimensions:

        (..., depth)

    Typical OceanEmbed input:

        (time, depth, latitude, longitude)

    or

        (time, latitude, longitude, depth)
    """

    if depth_dim not in temperature.dims:
        raise ValueError(
            f"Depth dimension '{depth_dim}' not found in "
            f"temperature dimensions: {temperature.dims}"
        )

    depths = temperature[depth_dim].values

    # Move depth to the final axis so the core function has a stable
    # contract independent of the input dimension ordering.
    temperature_reordered = temperature.transpose(
        *[d for d in temperature.dims if d != depth_dim],
        depth_dim,
    )

    values = temperature_reordered.values

    thermocline = calculate_thermocline_depth(
        values,
        depths,
        min_valid_levels=min_valid_levels,
    )

    output_dims = tuple(
        d for d in temperature_reordered.dims
        if d != depth_dim
    )

    output_coords = {
        d: temperature_reordered.coords[d]
        for d in output_dims
        if d in temperature_reordered.coords
    }

    return xr.DataArray(
        thermocline,
        dims=output_dims,
        coords=output_coords,
        name="thermocline_depth",
        attrs={
            "long_name": "Thermocline depth",
            "description": (
                "Depth midpoint of the adjacent level pair with "
                "maximum absolute vertical temperature gradient."
            ),
            "units": "m",
            "method": "maximum absolute vertical temperature gradient",
            "min_valid_levels": min_valid_levels,
        },
    )


# ---------------------------------------------------------------------------
# File-level helper
# ---------------------------------------------------------------------------

def calculate_thermocline_from_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    temperature_variable: str = "temperature_mean",
) -> xr.DataArray:
    """
    Calculate thermocline depth from a NetCDF temperature dataset.

    If output_path is supplied, writes a standalone NetCDF file.
    """

    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file does not exist: {input_path}"
        )

    with xr.open_dataset(input_path) as ds:
        if temperature_variable not in ds:
            raise KeyError(
                f"Temperature variable '{temperature_variable}' "
                f"not found. Available variables: {list(ds.data_vars)}"
            )

        thermocline = calculate_thermocline(
            ds[temperature_variable],
            depth_dim="depth",
        )

        result = thermocline.to_dataset()

        result.attrs.update(
            {
                "project": "OceanEmbed",
                "artifact": "thermocline_depth",
                "source": str(input_path),
            }
        )

        if output_path is not None:
            output_path = Path(output_path)
            output_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            result.to_netcdf(
                output_path,
                engine="netcdf4",
            )

    return thermocline