from pathlib import Path
import xarray as xr

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

def list_data_files() -> list[Path]:
    return sorted(DATA_DIR.glob("*.nc"))

def inspect_dataset(path: Path) -> dict:
    with xr.open_dataset(path) as ds:
        return {
            "file": path.name,
            "dimensions": {
                name: int(size)
                for name, size in ds.sizes.items()
            },
            "coordinates": list(ds.coords),
            "variables": list(ds.data_vars),
            "attributes": dict(ds.attrs),
        }

def inspect_all() -> list[dict]:
    return [
        inspect_dataset(path)
        for path in list_data_files()
    ]