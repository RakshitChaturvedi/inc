from pathlib import Path
import xarray as xr

ROOT = Path("data/raw/a12_test/2025-01-01_2025-01-07")

for nc in ROOT.rglob("*.nc"):
    print("\n" + "=" * 70)
    print(nc)

    with xr.open_dataset(nc) as ds:
        print("dims:", dict(ds.sizes))

        for name in ("latitude", "lat"):
            if name in ds.coords:
                v = ds[name]
                print(
                    f"{name}: "
                    f"{float(v.min()):.4f} → {float(v.max()):.4f}"
                )

        for name in ("longitude", "lon"):
            if name in ds.coords:
                v = ds[name]
                print(
                    f"{name}: "
                    f"{float(v.min()):.4f} → {float(v.max()):.4f}"
                )