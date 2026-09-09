from pathlib import Path
import xarray as xr

RAW = Path("data/raw")

for folder in sorted(RAW.iterdir()):
    if not folder.is_dir():
        continue

    files = sorted(folder.glob("*.nc"))

    if not files:
        print(f"{folder.name:12} : no .nc files")
        continue

    min_date = None
    max_date = None
    valid_files = 0

    for path in files:
        try:
            ds = xr.open_dataset(path)

            if "time" not in ds.coords and "time" not in ds:
                ds.close()
                continue

            time = ds["time"]

            if time.size == 0:
                ds.close()
                continue

            file_min = time.min().values
            file_max = time.max().values

            if min_date is None or file_min < min_date:
                min_date = file_min

            if max_date is None or file_max > max_date:
                max_date = file_max

            valid_files += 1
            ds.close()

        except Exception as e:
            print(f"  ERROR: {path.name}: {e}")

    print(
        f"{folder.name:12} : "
        f"{len(files):4} files | "
        f"{min_date} -> {max_date} | "
        f"{valid_files} with time"
    )