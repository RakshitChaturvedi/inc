from pathlib import Path
import numpy as np
import xarray as xr

from .pipeline import process_daily_forecast

DATE = "2025-01-02"
RAW_DATA_DIR = Path("data/raw/a12_test/2025-01-01_2025-01-07")
REGISTRY_DIR = Path("model-registry")
OUTPUT_PATH = Path("data/processed/input_tensor_normalized.nc")

CHANNELS = [
    "SST",
    "SSS",
    "SSHA",
    "wind_U",
    "wind_V",
    "current_U",
    "current_V",
    "wind_stress_curl",
    "latitude",
    "longitude",
    "sin_day_of_year",
    "cos_day_of_year",
]

print("=" * 70)
print("OCEANEMBED INPUT TENSOR EXPORT")
print("=" * 70)

print(f"Date       : {DATE}")
print(f"Raw data   : {RAW_DATA_DIR}")
print(f"Registry   : {REGISTRY_DIR}")
print(f"Output     : {OUTPUT_PATH}")

tensor, effective_ocean_mask = process_daily_forecast(
    DATE,
    RAW_DATA_DIR,
    REGISTRY_DIR,
)

effective_ocean_mask = np.asarray(
    effective_ocean_mask,
    dtype=bool,
)

if effective_ocean_mask.shape != (101, 241):
    raise RuntimeError(
        "Effective ocean mask has incorrect shape: "
        f"{effective_ocean_mask.shape}"
    )

effective_ocean_cells = int(
    effective_ocean_mask.sum()
)

excluded_cells = (
    effective_ocean_mask.size
    - effective_ocean_cells
)

print()
print("EFFECTIVE OCEAN MASK")
print(
    f"Computational ocean cells : "
    f"{effective_ocean_cells:,}"
)
print(
    f"Excluded cells             : "
    f"{excluded_cells:,}"
)

expected_shape = (1, 12, 101, 241)

if tensor.shape != expected_shape:
    raise ValueError(
        f"Unexpected tensor shape: {tensor.shape}; "
        f"expected {expected_shape}"
    )

if tensor.dtype != np.float32:
    raise ValueError(
        f"Unexpected tensor dtype: {tensor.dtype}; "
        "expected float32"
    )

nan_count = int(np.isnan(tensor).sum())

if nan_count != 0:
    raise ValueError(
        f"Tensor contains {nan_count} NaNs"
    )


print()
print("TENSOR CHECK")
print("------------")
print(f"Shape : {tensor.shape}")
print(f"Dtype : {tensor.dtype}")
print(f"NaNs  : {nan_count}")

mask_path = (
    REGISTRY_DIR
    / "oceanembed-v1.0.0"
    / "ocean_mask.nc"
)

with xr.open_dataset(mask_path) as mask_ds:
    latitude = mask_ds["latitude"].values
    longitude = mask_ds["longitude"].values

output_ds = xr.Dataset(
    {
        "input_tensor": (
            ["batch", "channel", "latitude", "longitude"],
            tensor,
        ),
        "effective_ocean_mask": (("latitude", "longitude"), effective_ocean_mask),
    },
    coords={
        "batch": [0],
        "channel": CHANNELS,
        "latitude": latitude,
        "longitude": longitude,
    },
)

output_ds.attrs.update(
    {
        "oceanembed_artifact": "input_tensor_normalized",
        "oceanembed_phase": 6,
        "normalization_method": "z-score",
        "normalization_formula": "(x - mean) / std",
        "source_date": DATE,
        "grid_resolution": "0.25 degrees",
        "grid_shape": "101 x 241",
        "channel_count": 12,
        "dtype": "float32",
        "persistent_unresolved_cells_excluded": 422,
        "status": "test/inference artifact",
        "effective_ocean_cells": int(effective_ocean_mask.sum()),
        "excluded_cells": int(effective_ocean_mask.size - effective_ocean_mask.sum()),
        "mask_source": "preprocessing effective_ocean_mask",
    }
)

output_ds["effective_ocean_mask"].attrs.update(
    {
        "long_name": "Effective OceanEmbed computational ocean mask",
        "description": (
            "True where all required input channels are computationally "
            "valid after spatial gap filling; False for permanent land "
            "and persistent unresolved cells."
        ),
        "valid_value": "True",
        "invalid_value": "False",
    }
)

output_ds["input_tensor"].attrs.update(
    {
        "description": (
            "Normalized OceanEmbed inference input tensor"
        ),
        "channels": ", ".join(CHANNELS),
    }
)

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

masked_tensor = tensor[0, :, :, :]

nonzero_excluded = np.count_nonzero(
    masked_tensor[:, ~effective_ocean_mask]
)

if nonzero_excluded != 0:
    raise RuntimeError(
        "Excluded cells contain non-zero tensor values: "
        f"{nonzero_excluded}"
    )
effective_values = tensor[
    0,
    :,
    effective_ocean_mask,
]

if not np.all(np.isfinite(effective_values)):
    raise RuntimeError(
        "Effective ocean cells contain NaN or infinite values."
    )

print()
print(f"Writing: {OUTPUT_PATH}")

output_ds.to_netcdf(
    OUTPUT_PATH,
    mode="w",
)

output_ds.close()


print()
print("=" * 70)
print("EXPORT SUCCESS")
print("=" * 70)
print(f"File : {OUTPUT_PATH}")
print(f"Shape: {expected_shape}")
print(f"Dtype: float32")
print(f"NaNs : 0")