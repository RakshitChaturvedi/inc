from __future__ import annotations

import numpy as np
import xarray as xr


# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

REFERENCE_DENSITY = 1025.0       # kg m^-3
SPECIFIC_HEAT = 3990.0           # J kg^-1 K^-1
REFERENCE_TEMPERATURE = 26.0     # °C

# Conversion:
# 1 kJ cm^-2 = 10^7 J m^-2
J_M2_TO_KJ_CM2 = 1.0e-7


# ---------------------------------------------------------------------------
# Core TCHP calculation
# ---------------------------------------------------------------------------

def calculate_tchp(
    temperature: np.ndarray,
    depths: np.ndarray,
    *,
    reference_temperature: float = REFERENCE_TEMPERATURE,
    reference_density: float = REFERENCE_DENSITY,
    specific_heat: float = SPECIFIC_HEAT,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Calculate Tropical Cyclone Heat Potential (TCHP).

    TCHP is the vertically integrated heat content above the 26°C
    reference temperature, from the surface to the depth where the
    temperature first reaches 26°C.

    Parameters
    ----------
    temperature:
        Temperature array with shape (..., depth).

    depths:
        1-D depth coordinate in metres.

    reference_temperature:
        Isotherm temperature defining the integration limit.
        Default: 26°C.

    reference_density:
        Reference seawater density in kg/m^3.

    specific_heat:
        Seawater specific heat capacity in J/(kg K).

    Returns
    -------
    tchp:
        TCHP in kJ/cm² with shape temperature.shape[:-1].

    d26:
        Depth of the 26°C isotherm in metres with shape
        temperature.shape[:-1].

    Notes
    -----
    Profiles for which the surface temperature is below 26°C receive
    NaN TCHP because a conventional 26°C warm-water column does not
    exist.

    Profiles that remain above 26°C through the deepest model level
    are integrated to the deepest available level and have d26 equal
    to that deepest level.
    """

    temperature = np.asarray(temperature, dtype=np.float64)
    depths = np.asarray(depths, dtype=np.float64)

    if temperature.ndim < 1:
        raise ValueError("temperature must have at least one dimension")

    if depths.ndim != 1:
        raise ValueError("depths must be one-dimensional")

    if temperature.shape[-1] != len(depths):
        raise ValueError(
            "Temperature depth dimension does not match depths: "
            f"{temperature.shape[-1]} != {len(depths)}"
        )

    if len(depths) < 2:
        raise ValueError("At least two depth levels are required")

    if not np.all(np.diff(depths) > 0):
        raise ValueError("Depths must be strictly increasing")

    output_shape = temperature.shape[:-1]

    tchp = np.full(output_shape, np.nan, dtype=np.float32)
    d26 = np.full(output_shape, np.nan, dtype=np.float32)

    # ---------------------------------------------------------------
    # Iterate over profiles.
    #
    # This intentionally processes one vertical profile at a time.
    # The production dataset is ~GB scale, so avoiding a giant
    # intermediate array is important.
    # ---------------------------------------------------------------

    flat_temperature = temperature.reshape(-1, len(depths))

    flat_tchp = tchp.reshape(-1)
    flat_d26 = d26.reshape(-1)

    for profile_idx in range(flat_temperature.shape[0]):

        profile = flat_temperature[profile_idx]

        # Require a valid surface value.
        if not np.isfinite(profile[0]):
            continue

        # Conventional TCHP requires the surface to be >= 26°C.
        if profile[0] < reference_temperature:
            continue

        # -----------------------------------------------------------
        # Find the first depth where temperature drops to <= 26°C.
        # -----------------------------------------------------------

        crossing = None

        for k in range(len(depths) - 1):

            t0 = profile[k]
            t1 = profile[k + 1]

            if not np.isfinite(t0) or not np.isfinite(t1):
                break

            if t0 >= reference_temperature and t1 <= reference_temperature:
                crossing = k
                break

        # -----------------------------------------------------------
        # Case 1:
        # 26°C isotherm exists inside the water column.
        # Interpolate its depth.
        # -----------------------------------------------------------

        if crossing is not None:

            k = crossing

            z0 = depths[k]
            z1 = depths[k + 1]

            t0 = profile[k]
            t1 = profile[k + 1]

            if t1 == t0:
                z26 = z1
            else:
                fraction = (
                    reference_temperature - t0
                ) / (t1 - t0)

                z26 = z0 + fraction * (z1 - z0)

            integration_depths = np.concatenate(
                [
                    depths[: k + 1],
                    np.asarray([z26]),
                ]
            )

            integration_temperature = np.concatenate(
                [
                    profile[: k + 1],
                    np.asarray([reference_temperature]),
                ]
            )

        # -----------------------------------------------------------
        # Case 2:
        # Entire available column remains >= 26°C.
        # Use deepest available model depth.
        # -----------------------------------------------------------

        else:

            valid = np.isfinite(profile)

            if not np.all(valid):
                continue

            z26 = depths[-1]

            integration_depths = depths
            integration_temperature = profile

        # -----------------------------------------------------------
        # Integrate excess temperature:
        #
        # H = rho * Cp * integral(T - 26) dz
        #
        # Units:
        #   kg/m³ * J/(kg K) * K * m
        #   = J/m²
        #
        # Convert J/m² -> kJ/cm².
        # -----------------------------------------------------------

        excess_temperature = (
            integration_temperature - reference_temperature
        )

        # Numerical integration using trapezoidal rule.
        integral = np.trapezoid(
            excess_temperature,
            integration_depths,
        )

        heat_content = (
            reference_density
            * specific_heat
            * integral
        )

        flat_tchp[profile_idx] = (
            heat_content * J_M2_TO_KJ_CM2
        )

        flat_d26[profile_idx] = z26

    return tchp, d26


# ---------------------------------------------------------------------------
# Xarray wrapper
# ---------------------------------------------------------------------------

def calculate_tchp_dataset(
    temperature: xr.DataArray,
    *,
    depth_dim: str = "depth",
) -> tuple[xr.DataArray, xr.DataArray]:
    """
    Calculate TCHP and D26 directly from an xarray temperature field.

    Expected input:

        (time, depth, latitude, longitude)

    or any array where `depth_dim` is the vertical dimension.

    Returns
    -------
    tchp:
        DataArray containing TCHP in kJ/cm².

    d26:
        DataArray containing 26°C isotherm depth in metres.
    """

    if depth_dim not in temperature.dims:
        raise ValueError(f"Depth dimension '{depth_dim}' not found in "f"{temperature.dims}")
    depths = temperature[depth_dim].values

    # Move depth to the final axis so the numerical routine has a stable contract.
    temperature_last = temperature.transpose(...,depth_dim,)
    tchp_values, d26_values = calculate_tchp(temperature_last.values,depths,)
    output_dims = tuple(dim for dim in temperature_last.dims if dim != depth_dim)
    output_coords = {dim: temperature_last.coords[dim] for dim in output_dims}

    tchp = xr.DataArray(
        tchp_values,
        dims=output_dims,
        coords=output_coords,
        name="tchp",
        attrs={
            "long_name": "Tropical Cyclone Heat Potential",
            "standard_name": "tropical_cyclone_heat_potential",
            "units": "kJ cm-2",
            "reference_temperature": 26.0,
            "reference_density": REFERENCE_DENSITY,
            "specific_heat": SPECIFIC_HEAT,
            "integration_method": "trapezoidal",
            "isotherm": "26°C",
        },
    )

    d26 = xr.DataArray(
        d26_values,
        dims=output_dims,
        coords=output_coords,
        name="d26",
        attrs={
            "long_name": "Depth of 26°C isotherm",
            "units": "m",
            "isotherm_temperature": 26.0,
            "interpolation": "linear",
        },
    )

    return tchp, d26

def add_tchp(ds: xr.Dataset, *, temperature_variable: str = "temperature_mean") -> xr.Dataset:
    # Add TCHP and D26 variables to an existing Dataset.

    if temperature_variable not in ds:
        raise KeyError(f"Temperature variable '{temperature_variable}' not found in dataset")

    tchp, d26 = calculate_tchp_dataset(ds[temperature_variable])

    output = ds.copy()
    output["tchp"] = tchp
    output["d26"] = d26
    output.attrs["tchp_computed"] = "true"
    output.attrs["tchp_reference_isotherm"] = "26°C"
    output.attrs["tchp_units"] = "kJ cm-2"

    return output