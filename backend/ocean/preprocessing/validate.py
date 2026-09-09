from __future__ import annotations

import numpy as np
from pathlib import Path

def validate_tensor(tensor: np.ndarray) -> bool:
    """
    Validates the preprocessed array against the OceanEmbed model contracts.
    """
    print("\n========================================")
    print("PREPROCESSING VALIDATION REPORT")
    print("========================================")
    
    passed = True

    # 1. Check Data Type
    print("[1] Data Type Check:")
    if tensor.dtype == np.float32:
        print("    PASS: Tensor is float32")
    else:
        print(f"    FAIL: Expected float32, got {tensor.dtype}")
        passed = False

    # 2. Check Shape Contract
    # Must exactly match [Batch, Channels, Lat, Lon] -> [1, 12, 101, 241]
    print("\n[2] Shape Contract Check:")
    expected_shape = (1, 12, 101, 241)
    if tensor.shape == expected_shape:
        print(f"    PASS: Shape is exactly {expected_shape}")
    else:
        print(f"    FAIL: Expected shape {expected_shape}, got {tensor.shape}")
        passed = False

    # 3. Check for NaNs
    print("\n[3] NaN Integrity Check:")
    if np.isnan(tensor).any():
        print("    FAIL: Tensor contains NaNs! The network will propagate these as invalid.")
        passed = False
    else:
        print("    PASS: No NaNs detected in the tensor.")

    # 4. Statistical Sanity Check per Channel
    print("\n[4] Statistical Distribution Check (Ocean Cells Only):")
    
    # Contract order from normalization_stats.json
    channel_order = [
        "SST", "SSS", "SSHA", "wind_U", "wind_V", 
        "current_U", "current_V", "wind_stress_curl", 
        "latitude", "longitude", "sin_doy", "cos_doy"
    ]
    
    # We ignore absolute 0.0 values in stats assuming they are masked land cells
    for i, name in enumerate(channel_order):
        # Slice the specific channel
        channel_data = tensor[0, i, :, :]
        
        # Filter out the zeros (land mask) to get pure ocean statistics
        ocean_pixels = channel_data[channel_data != 0.0]
        
        if len(ocean_pixels) == 0:
            print(f"    FAIL: Channel {name:>16} is entirely zeros. Masking error?")
            passed = False
            continue
            
        c_min = ocean_pixels.min()
        c_max = ocean_pixels.max()
        c_mean = ocean_pixels.mean()
        
        # Z-scores should generally fall within -10 to +10. 
        # sin/cos doy will be between -1 and 1.
        if i < 10 and (abs(c_mean) > 5.0 or c_max > 25.0 or c_min < -25.0):
            print(f"    WARN: {name:>16} | Min: {c_min:6.2f} | Max: {c_max:6.2f} | Mean: {c_mean:6.2f} (Suspicious Z-score)")
        else:
            print(f"    PASS: {name:>16} | Min: {c_min:6.2f} | Max: {c_max:6.2f} | Mean: {c_mean:6.2f}")

    print("========================================")
    if passed:
        print("✅ VALIDATION SUCCESS: Tensor is ready for inference.")
    else:
        print("❌ VALIDATION FAILED: See errors above.")
    print("========================================\n")
    
    return passed

# --- Quick Test Execution ---
if __name__ == "__main__":
    # You can import your pipeline here and run it on a sample date to test
    # from pipeline import process_daily_forecast
    # tensor = process_daily_forecast("2026-01-01", Path("data/raw"), Path("model-registry"))
    
    # For now, let's create a dummy valid tensor to test the validator itself
    print("Running validator on synthetic data...")
    dummy_tensor = np.random.randn(1, 12, 101, 241).astype(np.float32)
    validate_tensor(dummy_tensor)