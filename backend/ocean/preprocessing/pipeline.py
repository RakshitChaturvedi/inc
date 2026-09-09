from __future__ import annotations

from pathlib import Path
import glob
import xarray as xr
import numpy as np

# Import the geometric steps
from .schema import open_standardized
from .harmonize import (
    harmonize_sst, harmonize_sss, harmonize_ssh, 
    harmonize_wind, harmonize_currents
)
from .temporal import daily_mean, align_daily
from .spatial import subset_domain
from .regrid import create_target_grid, regrid_dataset

# Import the contract steps
from .features import compute_wind_stress_curl, add_spatial_features, add_temporal_features
from .normalize import apply_normalization
from .tensor import build_input_array

def find_file_for_date(directory: Path, date_str: str, prefix: str = "") -> Path:
    """Finds a NetCDF file matching a specific date string (e.g., '20260102' or '2026-01-02')."""
    # Convert '2026-01-02' to various common filename date formats
    clean_date = date_str.replace("-", "")
    
    # Search for files containing the date string
    pattern = f"*{clean_date}*.nc"
    matches = sorted(glob.glob(str(directory / pattern)))
    
    if not matches:
        # Fallback to general search if exact date match isn't found
        matches = sorted(glob.glob(str(directory / "*.nc")))
        
    if not matches:
        raise FileNotFoundError(f"No NetCDF files found for date {date_str} in {directory}")
        
    # Return the first match that contains the date, or safely fallback
    for m in matches:
        if clean_date in m or date_str in m:
            return Path(m)
            
    return Path(matches[0])

def process_daily_forecast(
    date_str: str, 
    raw_data_dir: Path, 
    registry_dir: Path
) -> np.ndarray:
    """
    Orchestrates the Phase B4 Preprocessing Pipeline.
    Takes a date and raw NetCDF paths, returns the final model-ready array.
    """
    
    # Configuration based on your Phase 2/5 domain
    domain = {"lat_min": 5.0, "lat_max": 30.0, "lon_min": 45.0, "lon_max": 105.0}
    target_grid = create_target_grid(**domain, resolution=0.25)
    
    print(f"--- Preprocessing Data for {date_str} ---")

    sst_path = find_file_for_date(raw_data_dir / "sst", date_str)
    sss_path = find_file_for_date(raw_data_dir / "sss", date_str)
    ssh_path = find_file_for_date(raw_data_dir / "ssh", date_str)
    wind_path = find_file_for_date(raw_data_dir / "wind", date_str)
    curr_path = find_file_for_date(raw_data_dir / "currents", date_str)

    print(f"Opening: {sst_path}")
    print(f"Opening: {sss_path}")
    print(f"Opening: {ssh_path}")
    print(f"Opening: {wind_path}")
    print(f"Opening: {curr_path}")
    
    # 1. Ingest, Schema, and Harmonize
    # (Assuming files are named systematically in raw_data_dir)
    ds_sst = harmonize_sst(open_standardized(sst_path, dataset_name="SST"))
    ds_sss = harmonize_sss(open_standardized(sss_path, dataset_name="SSS"))
    ds_ssh = harmonize_ssh(open_standardized(ssh_path, dataset_name="SSH"))
    ds_wind = harmonize_wind(open_standardized(wind_path, dataset_name="WIND"))
    ds_curr = harmonize_currents(open_standardized(curr_path, dataset_name="CURRENTS"))
    # 2. Temporal Alignment (Wind requires daily mean first)
    ds_wind = daily_mean(ds_wind)
    
    datasets = [ds_sst, ds_sss, ds_ssh, ds_wind, ds_curr]
    aligned = [align_daily(ds, start=date_str, end=date_str) for ds in datasets]
    
    # 3. Spatial Subsetting & 4. Regridding
    regridded = []
    for ds in aligned:
        subset = subset_domain(ds, **domain)
        regridded.append(regrid_dataset(subset, target_grid))
        
    # 5. Merge all variables into one Dataset
    merged = xr.merge(regridded)
    
    # 6. Feature Construction
    merged = compute_wind_stress_curl(merged)
    merged = add_spatial_features(merged)
    merged = add_temporal_features(merged)
    
    # 7. Normalization
    normalized = apply_normalization(merged, registry_dir)
    
    # 8. Tensor Formatting
    final_array = build_input_array(normalized, registry_dir)
    
    print(f"Success! Output array shape: {final_array.shape}")
    return final_array