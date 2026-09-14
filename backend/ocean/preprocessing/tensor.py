from __future__ import annotations

import numpy as np
import xarray as xr
from pathlib import Path

def build_input_array(
    ds: xr.Dataset, 
    registry_dir: Path,
    *,
    ocean_mask=None
) -> np.ndarray:
    """
    Extracts the 12 channels in the strict model contract order,
    masks out land pixels, and returns a shape [1, 12, 101, 241] array.
    """
    # The exact 12-channel order from normalization_stats.json
    channel_order = [
        "sst",
        "sss",
        "ssh",
        "wind_u",
        "wind_v",
        "current_u",
        "current_v",
        "wind_stress_curl",
        "latitude_var",
        "longitude_var",
        "sin_day_of_year",
        "cos_day_of_year"
    ]
    
    # 1. Stack the variables into a 3D NumPy array: [12, lat, lon]
    arrays = []
    for var in channel_order:
        if var not in ds.data_vars:
            raise ValueError(f"Missing required channel: {var}")
        # Extract the 2D grid for this variable
        arrays.append(ds[var].values.squeeze())
        
    stacked = np.stack(arrays, axis=0) # Shape: [12, 101, 241]
    
    # 2. Apply the Ocean Mask
    if ocean_mask is None:
        mask_path = registry_dir / "oceanembed-v1.0.0" / "ocean_mask.nc"
        if not mask_path.exists():
            raise FileNotFoundError(f"Ocean mask not found: {mask_path}")
        with xr.open_dataset(mask_path) as mask_ds:
            if "ocean_mask" not in mask_ds:
                raise ValueError("Registry mask file doesnt contain 'ocean_mask'")
            ocean_mask = (mask_ds["ocean_mask"].values.squeeze())
    ocean_mask = np.asarray(ocean_mask, dtype=bool)
    if ocean_mask.shape != (101, 241):
        raise ValueError(f"Ocean mask has shape {ocean_mask.shape}; expected (101, 241)")

    print()
    print("="*70)
    print("TENSOR MASKING")
    print("=" * 70)

    print(f"Computational ocean cells: {int(ocean_mask.sum())}")
    print(f"Exclusded cells :{int((~ocean_mask).sum())}")

    for i, var in enumerate(channel_order):
        channel = stacked[i]
        ocean_nan = (np.isnan(channel) & ocean_mask)
        excluded_nan = (np.isnan(channel) & ~ocean_mask)
        print(f"{var:22s} ocean NaNs={int(ocean_nan.sum()):5d}, excluded NaNs={int(excluded_nan.sum()):5d}")

    # apply computationa mask
    stacked = np.where(ocean_mask[None, :, :], stacked, 0.0)

    ocean_nan_after = (np.isnan(stacked) & ocean_mask[None, :, :])
    if ocean_nan_after.any():
        count = int(ocean_nan_after.sum())
        raise ValueError(f"NaNs remain inside the effective computational ocean mask: {count}")

    if np.isnan(stacked).any():
        raise ValueError("NaNs remain in final tensor after masking")

    # add batch dimension
    final_array = np.expand_dims(stacked, axis=0).astype(np.float32)
    if final_array.shape != (1, 12, 101, 241):
        raise ValueError(f"Final tensor has shape {final_array.shape}; expected (1, 12, 101, 241)")
    print()
    print(f"Final tensor shape: {final_array.shape}")
    print(f"Final tensor dtype: {final_array.dtype}")
    print(f"Final tensor NaNs: {int(np.isnan(final_array).sum())}")
    
    return final_array