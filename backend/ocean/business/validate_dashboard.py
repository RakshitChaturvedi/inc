from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DASHBOARD_PATH = (
    PROJECT_ROOT
    / "data"
    / "business"
    / "dashboard_ready.nc"
)


# ---------------------------------------------------------------------------
# Expected contract
# ---------------------------------------------------------------------------

EXPECTED_DIMS = {
    "time": 1419,
    "depth": 15,
    "latitude": 101,
    "longitude": 241,
}

EXPECTED_DEPTHS = np.array(
    [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000],
    dtype=np.float32,
)

REQUIRED_VARIABLES = [
    "temperature_mean",
    "temperature_std",
    "salinity_mean",
    "salinity_std",
    "tchp",
    "d26",
    "mld",
    "thermocline_depth",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check(condition: bool, label: str) -> None:
    print(f"  {label:<30}: {'PASS' if condition else 'FAIL'}")


def finite_summary(da: xr.DataArray) -> tuple[int, int]:
    """
    Compute finite/total counts without unnecessarily loading the whole
    dataset into memory.
    """
    values = da.values
    finite = int(np.isfinite(values).sum())
    total = int(values.size)
    return finite, total


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 70)
    print("OceanEmbed — Dashboard Artifact Validation")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. File existence
    # ------------------------------------------------------------------

    print("\n[1] File Check")
    print("-" * 70)

    check(DASHBOARD_PATH.exists(), "dashboard_ready.nc exists")

    if not DASHBOARD_PATH.exists():
        raise RuntimeError(f"Missing dashboard artifact: {DASHBOARD_PATH}")

    print(f"  Path                          : {DASHBOARD_PATH}")

    # ------------------------------------------------------------------
    # 2. Open dataset
    # ------------------------------------------------------------------

    print("\n[2] Dataset Structure")
    print("-" * 70)

    with xr.open_dataset(DASHBOARD_PATH) as ds:

        print(ds)

        # --------------------------------------------------------------
        # Dimensions
        # --------------------------------------------------------------

        print("\nDIMENSIONS")

        dimensions_pass = True

        for dim, expected in EXPECTED_DIMS.items():
            actual = ds.sizes.get(dim)

            passed = actual == expected
            dimensions_pass &= passed

            print(
                f"  {dim:<15}: "
                f"actual={actual}, expected={expected} "
                f"{'PASS' if passed else 'FAIL'}"
            )

        # --------------------------------------------------------------
        # Required variables
        # --------------------------------------------------------------

        print("\nREQUIRED VARIABLES")

        variables_pass = True

        for variable in REQUIRED_VARIABLES:
            passed = variable in ds.data_vars
            variables_pass &= passed

            print(
                f"  {variable:<25}: "
                f"{'PASS' if passed else 'FAIL'}"
            )

        # --------------------------------------------------------------
        # Coordinate contract
        # --------------------------------------------------------------

        print("\n[3] Coordinate Validation")
        print("-" * 70)

        # Depth
        if "depth" in ds.coords:
            actual_depths = ds["depth"].values

            depth_pass = (
                actual_depths.shape == EXPECTED_DEPTHS.shape
                and np.allclose(
                    actual_depths,
                    EXPECTED_DEPTHS,
                    atol=1e-5,
                )
            )

            check(depth_pass, "Depth coordinate")

            if not depth_pass:
                print(f"  Expected: {EXPECTED_DEPTHS}")
                print(f"  Actual  : {actual_depths}")

        else:
            check(False, "Depth coordinate")

        # Latitude
        latitude_pass = False

        if "latitude" in ds.coords:
            lat = ds["latitude"].values

            latitude_pass = (
                lat.ndim == 1
                and len(lat) == EXPECTED_DIMS["latitude"]
                and np.isfinite(lat).all()
                and np.all(np.diff(lat) > 0)
                and np.isclose(lat[0], 5.0)
                and np.isclose(lat[-1], 30.0)
            )

        check(latitude_pass, "Latitude coordinate")

        # Longitude
        longitude_pass = False

        if "longitude" in ds.coords:
            lon = ds["longitude"].values

            longitude_pass = (
                lon.ndim == 1
                and len(lon) == EXPECTED_DIMS["longitude"]
                and np.isfinite(lon).all()
                and np.all(np.diff(lon) > 0)
                and np.isclose(lon[0], 45.0)
                and np.isclose(lon[-1], 105.0)
            )

        check(longitude_pass, "Longitude coordinate")

        # Time
        time_pass = False

        if "time" in ds.coords:
            time = ds["time"].values

            time_pass = (
                time.ndim == 1
                and len(time) == EXPECTED_DIMS["time"]
                and np.all(np.diff(time) > np.timedelta64(0, "s"))
            )

        check(time_pass, "Time coordinate")

        # --------------------------------------------------------------
        # Variable dimensions
        # --------------------------------------------------------------

        print("\n[4] Variable Dimension Validation")
        print("-" * 70)

        expected_field_dims = (
            "time",
            "depth",
            "latitude",
            "longitude",
        )

        expected_business_dims = (
            "time",
            "latitude",
            "longitude",
        )

        dimension_pass = True

        for variable in REQUIRED_VARIABLES:

            if variable not in ds:
                continue

            da = ds[variable]

            if variable in {
                "temperature_mean",
                "temperature_std",
                "salinity_mean",
                "salinity_std",
            }:
                expected = expected_field_dims
            else:
                expected = expected_business_dims

            passed = da.dims == expected
            dimension_pass &= passed

            print(
                f"  {variable:<25}: "
                f"{'PASS' if passed else 'FAIL'} "
                f"{da.dims}"
            )

        # --------------------------------------------------------------
        # Shape validation
        # --------------------------------------------------------------

        print("\n[5] Shape Validation")
        print("-" * 70)

        shape_pass = True

        field_shape = (
            EXPECTED_DIMS["time"],
            EXPECTED_DIMS["depth"],
            EXPECTED_DIMS["latitude"],
            EXPECTED_DIMS["longitude"],
        )

        business_shape = (
            EXPECTED_DIMS["time"],
            EXPECTED_DIMS["latitude"],
            EXPECTED_DIMS["longitude"],
        )

        for variable in REQUIRED_VARIABLES:

            if variable not in ds:
                continue

            da = ds[variable]

            if variable in {
                "temperature_mean",
                "temperature_std",
                "salinity_mean",
                "salinity_std",
            }:
                expected_shape = field_shape
            else:
                expected_shape = business_shape

            passed = da.shape == expected_shape
            shape_pass &= passed

            print(
                f"  {variable:<25}: "
                f"{da.shape} "
                f"{'PASS' if passed else 'FAIL'}"
            )

        # --------------------------------------------------------------
        # Dtype validation
        # --------------------------------------------------------------

        print("\n[6] Data Type Validation")
        print("-" * 70)

        dtype_pass = True

        for variable in REQUIRED_VARIABLES:

            if variable not in ds:
                continue

            dtype = ds[variable].dtype

            passed = np.issubdtype(dtype, np.floating)
            dtype_pass &= passed

            print(
                f"  {variable:<25}: "
                f"{dtype} "
                f"{'PASS' if passed else 'FAIL'}"
            )

        # --------------------------------------------------------------
        # Finite-value validation
        # --------------------------------------------------------------

        print("\n[7] Data Sanity")
        print("-" * 70)

        finite_pass = True

        for variable in REQUIRED_VARIABLES:

            if variable not in ds:
                continue

            da = ds[variable]

            finite, total = finite_summary(da)

            ratio = finite / total if total else 0.0

            # Business fields should have at least some finite values.
            passed = finite > 0
            finite_pass &= passed

            print(
                f"  {variable:<25}: "
                f"{finite:,}/{total:,} finite "
                f"({ratio * 100:.2f}%) "
                f"{'PASS' if passed else 'FAIL'}"
            )

        # --------------------------------------------------------------
        # Business-variable sanity
        # --------------------------------------------------------------

        print("\n[8] Business Variable Sanity")
        print("-" * 70)

        business_pass = True

        # TCHP
        if "tchp" in ds:
            tchp = ds["tchp"]

            tchp_finite = tchp.values[np.isfinite(tchp.values)]

            passed = (
                tchp_finite.size > 0
                and np.nanmin(tchp_finite) >= 0
            )

            business_pass &= passed

            print(
                f"  {'TCHP non-negative':<30}: "
                f"{'PASS' if passed else 'FAIL'}"
            )

            if tchp_finite.size:
                print(
                    f"    range: "
                    f"{np.nanmin(tchp_finite):.4f} → "
                    f"{np.nanmax(tchp_finite):.4f}"
                )

        # D26
        if "d26" in ds:
            d26 = ds["d26"]

            finite = d26.values[np.isfinite(d26.values)]

            passed = finite.size > 0

            business_pass &= passed

            print(
                f"  {'D26 contains finite values':<30}: "
                f"{'PASS' if passed else 'FAIL'}"
            )

        # MLD
        if "mld" in ds:
            mld = ds["mld"]

            finite = mld.values[np.isfinite(mld.values)]

            passed = (
                finite.size > 0
                and np.nanmin(finite) >= 0
            )

            business_pass &= passed

            print(
                f"  {'MLD non-negative':<30}: "
                f"{'PASS' if passed else 'FAIL'}"
            )

        # Thermocline
        if "thermocline_depth" in ds:
            thermo = ds["thermocline_depth"]

            finite = thermo.values[np.isfinite(thermo.values)]

            passed = (
                finite.size > 0
                and np.nanmin(finite) >= 0
            )

            business_pass &= passed

            print(
                f"  {'Thermocline non-negative':<30}: "
                f"{'PASS' if passed else 'FAIL'}"
            )

        # --------------------------------------------------------------
        # Metadata
        # --------------------------------------------------------------

        print("\n[9] Metadata")
        print("-" * 70)

        print(f"  Attribute count : {len(ds.attrs)}")

        for key, value in ds.attrs.items():
            print(f"  {key:<25}: {value}")

        metadata_pass = True

        if "oceanembed_business_layer" in ds.attrs:
            metadata_pass &= True
        else:
            print("  Warning: oceanembed_business_layer attribute missing")

        # --------------------------------------------------------------
        # Final result
        # --------------------------------------------------------------

        overall_pass = all(
            [
                dimensions_pass,
                variables_pass,
                dimension_pass,
                shape_pass,
                dtype_pass,
                finite_pass,
                business_pass,
                latitude_pass,
                longitude_pass,
                time_pass,
                metadata_pass,
            ]
        )

        print("\n" + "=" * 70)
        print("FINAL VALIDATION")
        print("=" * 70)

        print(
            f"  Dimensions     : {'PASS' if dimensions_pass else 'FAIL'}"
        )
        print(
            f"  Variables      : {'PASS' if variables_pass else 'FAIL'}"
        )
        print(
            f"  Coordinates    : "
            f"{'PASS' if (latitude_pass and longitude_pass and time_pass) else 'FAIL'}"
        )
        print(
            f"  Dimensions/Shape: "
            f"{'PASS' if (dimension_pass and shape_pass) else 'FAIL'}"
        )
        print(
            f"  Dtypes         : {'PASS' if dtype_pass else 'FAIL'}"
        )
        print(
            f"  Finite Values  : {'PASS' if finite_pass else 'FAIL'}"
        )
        print(
            f"  Business Logic : {'PASS' if business_pass else 'FAIL'}"
        )

        print("\n" + "=" * 70)

        if overall_pass:
            print("DASHBOARD ARTIFACT VALIDATION: PASS")
        else:
            print("DASHBOARD ARTIFACT VALIDATION: FAIL")

        print("=" * 70)

        if not overall_pass:
            raise RuntimeError("dashboard_ready.nc failed validation.")


if __name__ == "__main__":
    main()