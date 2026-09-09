from __future__ import annotations

import glob
from pathlib import Path
import xarray as xr

from ocean.preprocessing.pipeline import process_daily_forecast
from ocean.preprocessing.validate import validate_tensor

def test_real_data_preprocessing():
    raw_dir = Path("data/raw")
    registry_dir = Path("model-registry")
    
    print("1. Scanning actual downloaded raw data directories...")
    
    # Dynamically find the first available file in each category
    sst_files = sorted(glob.glob(str(raw_dir / "sst" / "*.nc")))
    sss_files = sorted(glob.glob(str(raw_dir / "sss" / "*.nc")))
    ssh_files = sorted(glob.glob(str(raw_dir / "ssh" / "*.nc")))
    wind_files = sorted(glob.glob(str(raw_dir / "wind" / "*.nc")))
    curr_files = sorted(glob.glob(str(raw_dir / "currents" / "*.nc")))
    
    print(f"   Found SST files: {len(sst_files)}")
    print(f"   Found SSS files: {len(sss_files)}")
    print(f"   Found SSH files: {len(ssh_files)}")
    print(f"   Found Wind files: {len(wind_files)}")
    print(f"   Found Currents files: {len(curr_files)}")
    
    if not sst_files or not wind_files:
        print("❌ Error: Missing essential raw files in data/raw/. Check your download script output.")
        return

    # Pick the first real file's date or map it to your pipeline
    print("\n2. Running pipeline on real downloaded datasets...")
    
    # If your pipeline expects a specific date string, we can extract it or pass a date matching your files.
    # Let's run it using the date from the first available SST filename or a default safe string:
    sample_date = "2025-01-02" # Adjust this to match a date you actually downloaded
    
    try:
        final_tensor = process_daily_forecast(sample_date, raw_dir, registry_dir)
        
        print("\n3. Validating the real-data tensor...")
        validate_tensor(final_tensor)
        
    except Exception as e:
        print(f"\n❌ Pipeline encountered an error with real data: {e}")
        raise e

if __name__ == "__main__":
    test_real_data_preprocessing()