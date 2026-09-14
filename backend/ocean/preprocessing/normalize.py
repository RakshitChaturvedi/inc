from __future__ import annotations

import json
from pathlib import Path
import xarray as xr

def load_normalization_stats(registry_dir: Path) -> dict:
    """Loads the normalization statistics JSON from the Model Registry."""
    stats_path = registry_dir / "oceanembed-v1.0.0" / "normalization_stats.json"
    if not stats_path.exists():
        raise FileNotFoundError(f"Missing normalization stats at {stats_path}")
        
    with open(stats_path, "r") as f:
        return json.load(f)["statistics"]

def apply_normalization(ds: xr.Dataset, registry_dir: Path) -> xr.Dataset:
    """
    Applies Z-score normalization based on training statistics.
    Leaves temporal variables untouched.
    """
    stats = load_normalization_stats(registry_dir)
    
    # Map the dataset variables to the exact keys in normalization_stats.json
    variable_mapping = {
        "sst": "SST",
        "sss": "SSS",
        "ssh": "SSHA",
        "wind_u": "wind_U",
        "wind_v": "wind_V",
        "current_u": "current_U",
        "current_v": "current_V",
        "wind_stress_curl": "wind_stress_curl",
        "latitude_var": "latitude",
        "longitude_var": "longitude",
    }
    
    normalized_ds = ds.copy()
    
    for ds_var, json_key in variable_mapping.items():
        if ds_var in normalized_ds.data_vars:
            mean = stats[json_key]["mean"]
            std = stats[json_key]["std"]
            
            # Apply Z-score: (x - mean) / std
            normalized_ds[ds_var] = (normalized_ds[ds_var] - mean) / std
            
    return normalized_ds