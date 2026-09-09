from __future__ import annotations

from pathlib import Path
import numpy as np
import xarray as xr


PROJECT_ROOT = Path(__file__).resolve().parents[2]

EVALUATION_DIR = PROJECT_ROOT / "data" / "evaluation"

FILES = {
    "temperature": EVALUATION_DIR / "temperature_targets_masked.nc",
    "salinity": EVALUATION_DIR / "salinity_targets_masked.nc",
}


def inspect_file(name: str, path: Path) -> None:
    print("\n" + "=" * 80)
    print(f"{name.upper()} GROUND TRUTH")
    print("=" * 80)

    print(f"Path   : {path}")
    print(f"Exists : {path.exists()}")

    if not path.exists():
        print("STATUS : MISSING")
        return

    with xr.open_dataset(path) as ds:
        print("\nDATASET")
        print("-" * 80)
        print(ds)

        print("\nDIMENSIONS")
        print("-" * 80)
        for dim, size in ds.sizes.items():
            print(f"{dim:12s}: {size}")

        print("\nVARIABLES")
        print("-" * 80)

        for var_name, var in ds.data_vars.items():
            values = var.values

            finite = np.isfinite(values)

            print(f"\n{var_name}")
            print(f"  dims       : {var.dims}")
            print(f"  shape      : {var.shape}")
            print(f"  dtype      : {values.dtype}")
            print(f"  finite     : {finite.sum():,}")
            print(f"  NaN        : {np.isnan(values).sum():,}")

            if finite.any():
                print(f"  min        : {np.nanmin(values):.6f}")
                print(f"  max        : {np.nanmax(values):.6f}")
                print(f"  mean       : {np.nanmean(values):.6f}")

        print("\nCOORDINATES")
        print("-" * 80)

        for coord_name, coord in ds.coords.items():
            values = coord.values

            print(f"\n{coord_name}")
            print(f"  dims       : {coord.dims}")
            print(f"  shape      : {coord.shape}")

            if values.size:
                print(f"  first      : {values.flat[0]}")
                print(f"  last       : {values.flat[-1]}")

                if np.issubdtype(values.dtype, np.number):
                    print(f"  min        : {np.nanmin(values)}")
                    print(f"  max        : {np.nanmax(values)}")

        print("\nATTRIBUTES")
        print("-" * 80)

        for key, value in ds.attrs.items():
            print(f"{key}: {value}")


def compare_coordinates() -> None:
    print("\n" + "=" * 80)
    print("GROUND TRUTH COORDINATE COMPARISON")
    print("=" * 80)

    datasets = {}

    for name, path in FILES.items():
        if not path.exists():
            continue

        datasets[name] = xr.open_dataset(path)

    if len(datasets) < 2:
        print("Cannot compare: both files are required.")
        return

    temp = datasets["temperature"]
    salt = datasets["salinity"]

    print("\nCoordinate equality")
    print("-" * 80)

    all_coords = sorted(
        set(temp.coords.keys()) | set(salt.coords.keys())
    )

    for coord in all_coords:
        if coord not in temp.coords:
            print(f"{coord:12s}: missing from temperature")
            continue

        if coord not in salt.coords:
            print(f"{coord:12s}: missing from salinity")
            continue

        a = temp[coord].values
        b = salt[coord].values

        same_shape = a.shape == b.shape

        if same_shape:
            try:
                equal = np.array_equal(a, b)
            except TypeError:
                equal = False
        else:
            equal = False

        print(
            f"{coord:12s}: "
            f"shape={same_shape}, "
            f"values={equal}"
        )

    temp.close()
    salt.close()


def main() -> None:
    print("=" * 80)
    print("OceanEmbed — Ground Truth Inspection")
    print("=" * 80)

    print(f"\nEvaluation directory: {EVALUATION_DIR}")

    for name, path in FILES.items():
        inspect_file(name, path)

    compare_coordinates()

    print("\n" + "=" * 80)
    print("INSPECTION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()