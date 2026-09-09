from __future__ import annotations

from pathlib import Path

import xarray as xr

from .tchp import add_tchp
from .mld import add_mld
from .thermocline import calculate_thermocline


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_PATH = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "physics"
    / "physics_adjusted.nc"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "business"
)

OUTPUT_PATH = OUTPUT_DIR / "dashboard_ready.nc"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TEMPERATURE_VARIABLE = "temperature_mean"
SALINITY_VARIABLE = "salinity_mean"

REQUIRED_DIMS = (
    "time",
    "depth",
    "latitude",
    "longitude",
)

REQUIRED_DEPTHS = (
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
)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_input_dataset(ds: xr.Dataset) -> None:
    """
    Validate that physics_adjusted.nc satisfies the business-layer
    input contract.
    """

    print("\n" + "=" * 70)
    print("OceanEmbed — Business Layer Input Validation")
    print("=" * 70)

    # ---------------------------------------------------------------
    # Required variables
    # ---------------------------------------------------------------

    required_variables = (
        TEMPERATURE_VARIABLE,
        SALINITY_VARIABLE,
    )

    for variable in required_variables:
        if variable not in ds:
            raise KeyError(
                f"Required variable '{variable}' not found. "
                f"Available variables: {list(ds.data_vars)}"
            )

    print("Variables:")
    print(f"  {TEMPERATURE_VARIABLE:<20}: PASS")
    print(f"  {SALINITY_VARIABLE:<20}: PASS")

    # ---------------------------------------------------------------
    # Required dimensions
    # ---------------------------------------------------------------

    for dim in REQUIRED_DIMS:
        if dim not in ds.dims:
            raise ValueError(
                f"Required dimension '{dim}' missing. "
                f"Available dimensions: {list(ds.dims)}"
            )

    print("\nDimensions:")

    for dim in REQUIRED_DIMS:
        print(
            f"  {dim:<12}: "
            f"{ds.sizes[dim]}"
        )

    # ---------------------------------------------------------------
    # Temperature / salinity shape
    # ---------------------------------------------------------------

    temperature = ds[TEMPERATURE_VARIABLE]
    salinity = ds[SALINITY_VARIABLE]

    if temperature.dims != salinity.dims:
        raise ValueError(
            "Temperature and salinity dimensions differ:\n"
            f"  temperature: {temperature.dims}\n"
            f"  salinity:    {salinity.dims}"
        )

    if temperature.shape != salinity.shape:
        raise ValueError(
            "Temperature and salinity shapes differ:\n"
            f"  temperature: {temperature.shape}\n"
            f"  salinity:    {salinity.shape}"
        )

    print("\nField compatibility:")
    print("  Temperature/salinity dims  : PASS")
    print("  Temperature/salinity shape : PASS")

    # ---------------------------------------------------------------
    # Depth validation
    # ---------------------------------------------------------------

    actual_depths = tuple(
        float(depth)
        for depth in ds["depth"].values
    )

    expected_depths = tuple(REQUIRED_DEPTHS)

    if len(actual_depths) != len(expected_depths):
        raise ValueError(
            "Unexpected number of depth levels:\n"
            f"  expected: {len(expected_depths)}\n"
            f"  actual:   {len(actual_depths)}"
        )

    for actual, expected in zip(actual_depths, expected_depths):
        if abs(actual - expected) > 1e-4:
            raise ValueError(
                "Depth coordinate mismatch:\n"
                f"  expected: {expected_depths}\n"
                f"  actual:   {actual_depths}"
            )

    print("  Depth coordinate           : PASS")

    # ---------------------------------------------------------------
    # Coordinate sanity
    # ---------------------------------------------------------------

    for coordinate in (
        "time",
        "latitude",
        "longitude",
        "depth",
    ):
        values = ds[coordinate].values

        if values.size == 0:
            raise ValueError(
                f"Coordinate '{coordinate}' is empty."
            )

    print("  Coordinate sanity          : PASS")

    print("\nINPUT VALIDATION: PASS")


# ---------------------------------------------------------------------------
# Thermocline
# ---------------------------------------------------------------------------

def add_thermocline(
    ds: xr.Dataset,
    *,
    temperature_variable: str = TEMPERATURE_VARIABLE,
) -> xr.Dataset:
    """
    Add thermocline depth to the dashboard dataset.

    Uses the existing thermocline implementation.
    """

    if temperature_variable not in ds:
        raise KeyError(
            f"Temperature variable '{temperature_variable}' "
            "not found."
        )

    print("\nCalculating thermocline depth...")

    thermocline = calculate_thermocline(
        ds[temperature_variable],
        depth_dim="depth",
    )

    output = ds.copy()

    output["thermocline_depth"] = thermocline

    output.attrs["thermocline_computed"] = "true"
    output.attrs["thermocline_method"] = (
        "maximum absolute vertical temperature gradient"
    )

    return output


# ---------------------------------------------------------------------------
# Dashboard validation
# ---------------------------------------------------------------------------

def validate_dashboard_dataset(ds: xr.Dataset) -> None:
    """
    Validate that all business variables were successfully produced.
    """

    print("\n" + "=" * 70)
    print("OceanEmbed — Dashboard Dataset Validation")
    print("=" * 70)

    required_business_variables = (
        "tchp",
        "d26",
        "mld",
        "thermocline_depth",
    )

    for variable in required_business_variables:

        if variable not in ds:
            raise RuntimeError(
                f"Business variable '{variable}' was not generated."
            )

        data = ds[variable]

        print(
            f"  {variable:<22}: "
            f"shape={data.shape}, "
            f"dtype={data.dtype}"
        )

    # ---------------------------------------------------------------
    # Spatial dimensions
    # ---------------------------------------------------------------

    expected_spatial_dims = (
        "time",
        "latitude",
        "longitude",
    )

    for variable in required_business_variables:

        dims = ds[variable].dims

        if dims != expected_spatial_dims:
            raise RuntimeError(
                f"Unexpected dimensions for '{variable}': "
                f"{dims}; expected {expected_spatial_dims}"
            )

    print("\nBusiness variable dimensions : PASS")

    # ---------------------------------------------------------------
    # Basic finite-value checks
    # ---------------------------------------------------------------

    for variable in required_business_variables:

        data = ds[variable]

        finite_count = int(
            data.notnull().sum().values
        )

        total_count = data.size

        print(
            f"  {variable:<22}: "
            f"{finite_count:,}/{total_count:,} finite"
        )

        if finite_count == 0:
            raise RuntimeError(
                f"Business variable '{variable}' contains "
                "no valid values."
            )

    print("\nDASHBOARD VALIDATION: PASS")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:

    print("=" * 70)
    print("OceanEmbed — Dashboard Builder")
    print("=" * 70)

    # ---------------------------------------------------------------
    # 1. Check input
    # ---------------------------------------------------------------

    print("\n[1] Loading physics-adjusted dataset")
    print(f"Input: {INPUT_PATH}")

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Physics-adjusted dataset not found:\n{INPUT_PATH}"
        )

    # ---------------------------------------------------------------
    # 2. Open dataset
    #
    # Do not call .load() here.
    #
    # physics_adjusted.nc is large. Business calculations already
    # operate through NumPy/xarray and we avoid unnecessarily loading
    # unrelated variables into RAM.
    # ---------------------------------------------------------------

    with xr.open_dataset(INPUT_PATH) as ds:

        validate_input_dataset(ds)

        # -----------------------------------------------------------
        # 3. TCHP + D26
        # -----------------------------------------------------------

        print("\n[2] Calculating TCHP and D26")

        ds_business = add_tchp(
            ds,
            temperature_variable=TEMPERATURE_VARIABLE,
        )

        print("  TCHP : PASS")
        print("  D26  : PASS")

        # -----------------------------------------------------------
        # 4. MLD
        # -----------------------------------------------------------

        print("\n[3] Calculating Mixed Layer Depth")

        ds_business = add_mld(
            ds_business,
            temperature_variable=TEMPERATURE_VARIABLE,
            salinity_variable=SALINITY_VARIABLE,
        )

        print("  MLD  : PASS")

        # -----------------------------------------------------------
        # 5. Thermocline
        # -----------------------------------------------------------

        print("\n[4] Calculating thermocline depth")

        ds_business = add_thermocline(
            ds_business,
            temperature_variable=TEMPERATURE_VARIABLE,
        )

        print("  Thermocline : PASS")

        # -----------------------------------------------------------
        # 6. Final validation
        # -----------------------------------------------------------

        validate_dashboard_dataset(ds_business)

        # -----------------------------------------------------------
        # 7. Dashboard metadata
        # -----------------------------------------------------------

        ds_business.attrs.update(
            {
                "project": "OceanEmbed",
                "artifact": "dashboard_ready",
                "source": str(INPUT_PATH),
                "business_layer": "completed",
                "dashboard_variables": (
                    "temperature_mean,"
                    "salinity_mean,"
                    "temperature_std,"
                    "salinity_std,"
                    "tchp,"
                    "d26,"
                    "mld,"
                    "thermocline_depth"
                ),
            }
        )

        # -----------------------------------------------------------
        # 8. Save
        # -----------------------------------------------------------

        OUTPUT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        print("\n[5] Writing dashboard artifact")
        print(f"Output: {OUTPUT_PATH}")

        ds_business.to_netcdf(
            OUTPUT_PATH,
            engine="netcdf4",
        )

        print("  Write : PASS")

    # ---------------------------------------------------------------
    # 9. Re-open final artifact and verify it actually exists
    # ---------------------------------------------------------------

    if not OUTPUT_PATH.exists():
        raise RuntimeError(
            "Dashboard output was not created."
        )

    print("\n[6] Final artifact verification")

    with xr.open_dataset(OUTPUT_PATH) as final_ds:

        print(
            f"  Dimensions : {dict(final_ds.sizes)}"
        )

        print(
            f"  Variables  : {list(final_ds.data_vars)}"
        )

        for variable in (
            "tchp",
            "d26",
            "mld",
            "thermocline_depth",
        ):
            if variable not in final_ds:
                raise RuntimeError(
                    f"Final artifact is missing '{variable}'."
                )

    print("\n" + "=" * 70)
    print("DASHBOARD BUILD COMPLETE")
    print("=" * 70)
    print(f"Output: {OUTPUT_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    main()