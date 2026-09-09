from __future__ import annotations

import numpy as np
import xarray as xr
from pathlib import Path

def build_input_array(
    ds: xr.Dataset, 
    registry_dir: Path
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
    mask_path = registry_dir / "oceanembed-v1" / "ocean_mask.nc"
    if mask_path.exists():
        with xr.open_dataset(mask_path) as mask_ds:
            # Assuming mask_value = 1 for ocean, 0/NaN for land
            mask = mask_ds["mask"].values.squeeze()
            # Broadcast mask across all 12 channels
            stacked = np.where(mask == 1, stacked, 0.0)
            
    # 3. Add the batch dimension: [1, 12, 101, 241]
    return np.expand_dims(stacked, axis=0).astype(np.float32)