import os
from pathlib import Path
import numpy as np
import xarray as xr

def generate_sample_dataset():
    backend_root = Path(__file__).resolve().parents[1]
    business_dir = backend_root / "data" / "business"
    business_dir.mkdir(parents=True, exist_ok=True)
    out_file = business_dir / "dashboard_ready.nc"

    times = np.array([
        "2026-08-25",
        "2026-08-26",
        "2026-08-27"
    ], dtype="datetime64[ns]")
    
    depths = np.array([0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000], dtype=np.float32)
    lats = np.round(np.arange(5.0, 30.25, 0.25, dtype=np.float32), 2)
    lons = np.round(np.arange(45.0, 105.25, 0.25, dtype=np.float32), 2)

    n_time = len(times)
    n_depth = len(depths)
    n_lat = len(lats)
    n_lon = len(lons)

    # Create coordinate grids for 2D fields
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    
    # Mathematical eddy / physical approximation for ocean fields
    eddy = np.sin((lon_grid - 57) / 5.0) * np.cos((lat_grid - 14) / 4.0)
    
    # 2D variables: (time, lat, lon)
    tchp_2d = np.clip(62.0 + eddy * 22.0 + np.cos(lat_grid / 4.0) * 12.0, 10.0, 130.0).astype(np.float32)
    d26_2d = np.clip(72.0 + eddy * 28.0 + np.sin(lat_grid / 4.0) * 14.0, 10.0, 160.0).astype(np.float32)
    mld_2d = np.clip(33.0 + eddy * 15.0 + np.cos(lon_grid / 8.0) * 9.0, 8.0, 110.0).astype(np.float32)
    thermocline_2d = np.clip(95.0 + eddy * 20.0 + np.sin(lat_grid / 6.0) * 15.0, 30.0, 200.0).astype(np.float32)

    tchp_data = np.tile(tchp_2d[np.newaxis, :, :], (n_time, 1, 1))
    d26_data = np.tile(d26_2d[np.newaxis, :, :], (n_time, 1, 1))
    mld_data = np.tile(mld_2d[np.newaxis, :, :], (n_time, 1, 1))
    thermocline_data = np.tile(thermocline_2d[np.newaxis, :, :], (n_time, 1, 1))

    # 3D variables: (time, depth, lat, lon)
    temp_mean = np.zeros((n_time, n_depth, n_lat, n_lon), dtype=np.float32)
    temp_std = np.zeros((n_time, n_depth, n_lat, n_lon), dtype=np.float32)
    sal_mean = np.zeros((n_time, n_depth, n_lat, n_lon), dtype=np.float32)
    sal_std = np.zeros((n_time, n_depth, n_lat, n_lon), dtype=np.float32)

    for d_idx, d in enumerate(depths):
        thermocline_effect = np.exp(-((d - 110.0) / 100.0) ** 2)
        
        t_val = np.clip(29.2 - d * 0.011 + eddy * 1.3 - thermocline_effect * 2.4, 3.0, 31.0)
        s_val = np.clip(34.3 + eddy * 0.45 + d * 0.0009, 31.0, 37.0)
        unc_val = np.clip(0.18 + np.abs(eddy) * 0.38 + thermocline_effect * 0.24, 0.1, 1.2)
        s_unc_val = np.clip(0.05 + unc_val * 0.15, 0.02, 0.5)

        for t_idx in range(n_time):
            temp_mean[t_idx, d_idx] = t_val
            temp_std[t_idx, d_idx] = unc_val
            sal_mean[t_idx, d_idx] = s_val
            sal_std[t_idx, d_idx] = s_unc_val

    ds = xr.Dataset(
        data_vars={
            "temperature_mean": (["time", "depth", "latitude", "longitude"], temp_mean),
            "temperature_std": (["time", "depth", "latitude", "longitude"], temp_std),
            "salinity_mean": (["time", "depth", "latitude", "longitude"], sal_mean),
            "salinity_std": (["time", "depth", "latitude", "longitude"], sal_std),
            "tchp": (["time", "latitude", "longitude"], tchp_data),
            "d26": (["time", "latitude", "longitude"], d26_data),
            "mld": (["time", "latitude", "longitude"], mld_data),
            "thermocline_depth": (["time", "latitude", "longitude"], thermocline_data),
        },
        coords={
            "time": times,
            "depth": depths,
            "latitude": lats,
            "longitude": lons,
        },
        attrs={
            "description": "OceanEmbed development/local sample dataset",
            "source": "Synthesized OceanEmbed daily predictions for frontend integration",
            "model_version": "v1.0.0",
        }
    )

    ds.to_netcdf(out_file)
    print(f"Created sample dataset at {out_file} (size: {out_file.stat().st_size / (1024*1024):.2f} MB)")

if __name__ == "__main__":
    generate_sample_dataset()
