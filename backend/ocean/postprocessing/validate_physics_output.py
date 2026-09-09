from pathlib import Path

import numpy as np
import xarray as xr


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "physics"
    / "physics_adjusted.nc"
)

EXPECTED_DIMS = {
    "time": 1419,
    "depth": 15,
    "latitude": 101,
    "longitude": 241,
}

EXPECTED_DEPTHS = np.array([
    0,
    5,
    10,
    20,
    30,
    50,
    75,
    100,
    125,
    150,
    200,
    300,
    500,
    700,
    1000,
], dtype=np.float32)

EXPECTED_VARIABLES = [
    "temperature_mean",
    "salinity_mean",
    "temperature_std",
    "salinity_std",
]


def fail(message: str) -> None:
    raise RuntimeError(
        f"\nPHYSICS OUTPUT VALIDATION FAILED\n{message}"
    )


def main() -> None:
    print("=" * 72)
    print("OceanEmbed — Physics-Adjusted Output Validation")
    print("=" * 72)

    print(f"Input: {INPUT_PATH}")

    if not INPUT_PATH.exists():
        fail(f"Output file does not exist: {INPUT_PATH}")

    with xr.open_dataset(INPUT_PATH) as ds:

        # ---------------------------------------------------------------
        # Dataset structure
        # ---------------------------------------------------------------

        print("\n[1] Dataset structure")

        print(ds)

        actual_dims = dict(ds.sizes)

        if actual_dims != EXPECTED_DIMS:
            fail(
                f"Dimension mismatch.\n"
                f"Expected: {EXPECTED_DIMS}\n"
                f"Actual:   {actual_dims}"
            )

        print("PASS: dimensions")

        # ---------------------------------------------------------------
        # Variables
        # ---------------------------------------------------------------

        print("\n[2] Variables")

        actual_variables = list(ds.data_vars)

        print(f"Variables: {actual_variables}")

        missing = [
            v for v in EXPECTED_VARIABLES
            if v not in ds.data_vars
        ]

        unexpected = [
            v for v in actual_variables
            if v not in EXPECTED_VARIABLES
        ]

        if missing:
            fail(f"Missing variables: {missing}")

        if unexpected:
            print(f"WARNING: unexpected variables: {unexpected}")

        print("PASS: required variables")

        # ---------------------------------------------------------------
        # Shapes and dtypes
        # ---------------------------------------------------------------

        print("\n[3] Variable contracts")

        expected_shape = (
            EXPECTED_DIMS["time"],
            EXPECTED_DIMS["depth"],
            EXPECTED_DIMS["latitude"],
            EXPECTED_DIMS["longitude"],
        )

        for name in EXPECTED_VARIABLES:
            da = ds[name]

            print(
                f"  {name:<18}"
                f"shape={da.shape}"
                f" dtype={da.dtype}"
            )

            if da.shape != expected_shape:
                fail(
                    f"{name}: incorrect shape.\n"
                    f"Expected: {expected_shape}\n"
                    f"Actual:   {da.shape}"
                )

            if da.dtype != np.float32:
                fail(
                    f"{name}: expected float32, "
                    f"got {da.dtype}"
                )

        print("PASS: shapes and dtypes")

        # ---------------------------------------------------------------
        # Coordinates
        # ---------------------------------------------------------------

        print("\n[4] Coordinates")

        required_coords = [
            "time",
            "depth",
            "latitude",
            "longitude",
        ]

        for coord in required_coords:
            if coord not in ds.coords:
                fail(f"Missing coordinate: {coord}")

        actual_depths = ds.depth.values.astype(np.float32)

        if not np.allclose(
            actual_depths,
            EXPECTED_DEPTHS,
            rtol=0,
            atol=1e-5,
        ):
            fail(
                f"Depth coordinate mismatch.\n"
                f"Expected: {EXPECTED_DEPTHS.tolist()}\n"
                f"Actual:   {actual_depths.tolist()}"
            )

        print("PASS: depth coordinate")

        # ---------------------------------------------------------------
        # Time
        # ---------------------------------------------------------------

        if ds.time.values[0] != np.datetime64("2021-01-01"):
            fail(
                f"Unexpected first timestamp: "
                f"{ds.time.values[0]}"
            )

        if ds.time.values[-1] != np.datetime64("2024-11-19"):
            fail(
                f"Unexpected last timestamp: "
                f"{ds.time.values[-1]}"
            )

        print(
            f"Time: {ds.time.values[0]} -> "
            f"{ds.time.values[-1]}"
        )

        print("PASS: time coordinate")

        # ---------------------------------------------------------------
        # Finite values
        # ---------------------------------------------------------------

        print("\n[5] Numerical validity")

        for name in EXPECTED_VARIABLES:
            values = ds[name].values

            finite = np.isfinite(values)

            finite_count = int(finite.sum())
            total_count = values.size

            print(
                f"  {name:<18}"
                f"finite={finite_count:,}/{total_count:,}"
            )

            if finite_count != total_count:
                fail(
                    f"{name} contains "
                    f"{total_count - finite_count:,} "
                    f"non-finite values"
                )

        print("PASS: all values finite")

        # ---------------------------------------------------------------
        # Standard deviation validity
        # ---------------------------------------------------------------

        print("\n[6] Ensemble uncertainty validity")

        for name in [
            "temperature_std",
            "salinity_std",
        ]:
            values = ds[name].values

            minimum = float(values.min())
            maximum = float(values.max())

            print(
                f"  {name:<18}"
                f"min={minimum:.8f}"
                f" max={maximum:.8f}"
            )

            if minimum < 0:
                fail(
                    f"{name} contains negative "
                    f"standard deviations"
                )

        print("PASS: standard deviations valid")

        # ---------------------------------------------------------------
        # Physics metadata
        # ---------------------------------------------------------------

        print("\n[7] Physics metadata")

        print(
            "convective_adjustment:",
            ds.attrs.get("convective_adjustment")
        )

        if ds.attrs.get("convective_adjustment") != "applied":
            fail(
                "Dataset does not declare "
                "'convective_adjustment=applied'"
            )

        print("PASS: convective adjustment metadata")

        # ---------------------------------------------------------------
        # Summary
        # ---------------------------------------------------------------

        print("\n" + "=" * 72)
        print("PHYSICS OUTPUT VALIDATION: PASS")
        print("=" * 72)

        print(f"Days          : {ds.sizes['time']}")
        print(f"Depths        : {ds.sizes['depth']}")
        print(
            f"Spatial grid  : "
            f"{ds.sizes['latitude']} × "
            f"{ds.sizes['longitude']}"
        )

        print(
            f"Time range    : "
            f"{ds.time.values[0]} -> "
            f"{ds.time.values[-1]}"
        )

        print(
            f"Adjustment    : "
            f"{ds.attrs.get('convective_adjustment')}"
        )

        print("=" * 72)


if __name__ == "__main__":
    main()