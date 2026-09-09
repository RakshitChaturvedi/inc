from __future__ import annotations

import numpy as np
import xarray as xr

from ocean.postprocessing.eos import linear_eos


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REFERENCE_DEPTH = 10.0          # m
DENSITY_THRESHOLD = 0.03        # kg/m^3
MIN_VALID_LEVELS = 2


# ---------------------------------------------------------------------------
# Core MLD calculation
# ---------------------------------------------------------------------------

def calculate_mld(
    temperature: np.ndarray,
    salinity: np.ndarray,
    depths: np.ndarray,
    *,
    reference_depth: float = REFERENCE_DEPTH,
    density_threshold: float = DENSITY_THRESHOLD,
    min_valid_levels: int = MIN_VALID_LEVELS,
) -> np.ndarray:
    """
    Calculate Mixed Layer Depth using a density threshold criterion.

    The reference density is taken at the model depth closest to
    `reference_depth`.

    MLD is the deepest depth where:

        rho(z) - rho(reference) <= density_threshold

    Parameters
    ----------
    temperature:
        Temperature array with shape (..., depth).

    salinity:
        Salinity array with shape (..., depth).

    depths:
        1-D depth coordinate in metres.

    reference_depth:
        Reference depth for the density criterion.

    density_threshold:
        Density difference threshold in kg/m^3.

    min_valid_levels:
        Minimum number of valid vertical levels required.

    Returns
    -------
    mld:
        Mixed Layer Depth in metres with shape temperature.shape[:-1].

    Notes
    -----
    This implementation uses the project's existing `linear_eos`
    implementation so that the business layer remains consistent with
    the physics layer.
    """

    temperature = np.asarray(temperature, dtype=np.float32)
    salinity = np.asarray(salinity, dtype=np.float32)
    depths = np.asarray(depths, dtype=np.float32)

    if temperature.shape != salinity.shape:
        raise ValueError(
            "Temperature and salinity shapes must match: "
            f"{temperature.shape} != {salinity.shape}"
        )

    if temperature.ndim < 1:
        raise ValueError(
            "Temperature must have at least one dimension"
        )

    if depths.ndim != 1:
        raise ValueError("Depths must be one-dimensional")

    if temperature.shape[-1] != len(depths):
        raise ValueError(
            "Depth dimension does not match depths: "
            f"{temperature.shape[-1]} != {len(depths)}"
        )

    if len(depths) < 2:
        raise ValueError(
            "At least two depth levels are required"
        )

    if not np.all(np.diff(depths) > 0):
        raise ValueError(
            "Depths must be strictly increasing"
        )

    if density_threshold <= 0:
        raise ValueError(
            "density_threshold must be positive"
        )

    # ---------------------------------------------------------------
    # Find model level nearest the requested reference depth.
    # ---------------------------------------------------------------

    reference_index = int(
        np.argmin(
            np.abs(depths - reference_depth)
        )
    )

    actual_reference_depth = depths[reference_index]

    # ---------------------------------------------------------------
    # Calculate density.
    #
    # linear_eos accepts tensors, so use torch through the existing
    # physics implementation.
    # ---------------------------------------------------------------

    import torch

    temperature_tensor = torch.from_numpy(temperature)
    salinity_tensor = torch.from_numpy(salinity)

    density = linear_eos(
        temperature_tensor,
        salinity_tensor,
    ).numpy()

    output_shape = temperature.shape[:-1]

    mld = np.full(
        output_shape,
        np.nan,
        dtype=np.float32,
    )

    flat_density = density.reshape(-1, len(depths))
    flat_temperature = temperature.reshape(-1, len(depths))
    flat_salinity = salinity.reshape(-1, len(depths))
    flat_mld = mld.reshape(-1)

    # ---------------------------------------------------------------
    # Process each vertical profile.
    # ---------------------------------------------------------------

    for profile_idx in range(flat_density.shape[0]):

        rho = flat_density[profile_idx]
        temp = flat_temperature[profile_idx]
        salt = flat_salinity[profile_idx]

        valid = (
            np.isfinite(rho)
            & np.isfinite(temp)
            & np.isfinite(salt)
        )

        if valid.sum() < min_valid_levels:
            continue

        # Reference level itself must be valid.
        if not valid[reference_index]:
            continue

        reference_density_value = rho[reference_index]

        density_difference = (
            rho - reference_density_value
        )

        # -----------------------------------------------------------
        # Find deepest valid level satisfying the MLD criterion.
        # -----------------------------------------------------------

        within_mixed_layer = (
            valid
            & (
                density_difference
                <= density_threshold
            )
        )

        valid_indices = np.flatnonzero(
            within_mixed_layer
        )

        if len(valid_indices) == 0:
            continue

        deepest_index = valid_indices[-1]

        # -----------------------------------------------------------
        # If the transition occurs between two model levels,
        # linearly interpolate the threshold crossing.
        # -----------------------------------------------------------

        if deepest_index < len(depths) - 1:

            next_index = deepest_index + 1

            if valid[next_index]:

                d0 = density_difference[deepest_index]
                d1 = density_difference[next_index]

                if (
                    d0 <= density_threshold
                    and d1 > density_threshold
                    and d1 != d0
                ):
                    fraction = (
                        density_threshold - d0
                    ) / (d1 - d0)

                    interpolated_depth = (
                        depths[deepest_index]
                        + fraction
                        * (
                            depths[next_index]
                            - depths[deepest_index]
                        )
                    )

                    flat_mld[profile_idx] = (
                        interpolated_depth
                    )
                    continue

        flat_mld[profile_idx] = (
            depths[deepest_index]
        )

    return mld


# ---------------------------------------------------------------------------
# Xarray wrapper
# ---------------------------------------------------------------------------

def calculate_mld_dataset(
    temperature: xr.DataArray,
    salinity: xr.DataArray,
    *,
    depth_dim: str = "depth",
    reference_depth: float = REFERENCE_DEPTH,
    density_threshold: float = DENSITY_THRESHOLD,
) -> xr.DataArray:
    """
    Calculate MLD from xarray temperature and salinity fields.
    """

    if depth_dim not in temperature.dims:
        raise ValueError(
            f"Depth dimension '{depth_dim}' not found "
            f"in temperature: {temperature.dims}"
        )

    if depth_dim not in salinity.dims:
        raise ValueError(
            f"Depth dimension '{depth_dim}' not found "
            f"in salinity: {salinity.dims}"
        )

    if temperature.dims != salinity.dims:
        raise ValueError(
            "Temperature and salinity dimensions must match: "
            f"{temperature.dims} != {salinity.dims}"
        )

    depths = temperature[depth_dim].values

    temperature_last = temperature.transpose(
        ...,
        depth_dim,
    )

    salinity_last = salinity.transpose(
        ...,
        depth_dim,
    )

    mld_values = calculate_mld(
        temperature_last.values,
        salinity_last.values,
        depths,
        reference_depth=reference_depth,
        density_threshold=density_threshold,
    )

    output_dims = tuple(
        dim
        for dim in temperature_last.dims
        if dim != depth_dim
    )

    output_coords = {
        dim: temperature_last.coords[dim]
        for dim in output_dims
    }

    return xr.DataArray(
        mld_values,
        dims=output_dims,
        coords=output_coords,
        name="mld",
        attrs={
            "long_name": "Mixed Layer Depth",
            "standard_name": "ocean_mixed_layer_thickness",
            "units": "m",
            "method": "density_threshold",
            "density_threshold": density_threshold,
            "reference_depth": reference_depth,
            "reference_density_definition": (
                "density at model level nearest reference depth"
            ),
        },
    )


# ---------------------------------------------------------------------------
# Dataset convenience function
# ---------------------------------------------------------------------------

def add_mld(
    ds: xr.Dataset,
    *,
    temperature_variable: str = "temperature_mean",
    salinity_variable: str = "salinity_mean",
) -> xr.Dataset:
    """
    Add MLD to an existing Dataset.
    """

    if temperature_variable not in ds:
        raise KeyError(
            f"Temperature variable '{temperature_variable}' "
            "not found"
        )

    if salinity_variable not in ds:
        raise KeyError(
            f"Salinity variable '{salinity_variable}' "
            "not found"
        )

    mld = calculate_mld_dataset(
        ds[temperature_variable],
        ds[salinity_variable],
    )

    output = ds.copy()

    output["mld"] = mld

    output.attrs["mld_computed"] = "true"
    output.attrs["mld_method"] = "density_threshold"
    output.attrs["mld_density_threshold"] = DENSITY_THRESHOLD
    output.attrs["mld_reference_depth"] = REFERENCE_DEPTH

    return output