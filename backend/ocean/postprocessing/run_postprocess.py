from __future__ import annotations

from pathlib import Path
import numpy as np
import torch
import xarray as xr

# Import your physics modules
from .convective_adjustment import (
    apply_convective_adjustment,
    calculate_inversion_statistics,
)

# ---------------------------------------------------------------------------
# Paths & Config
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Updated to expect member-level predictions from the inference step
INPUT_PATH = PROJECT_ROOT / "backend" / "data" / "inference" / "ensemble_member_predictions.nc"
MASK_PATH = PROJECT_ROOT / "backend" / "model-registry" / "oceanembed-v1.0.0" / "ocean_mask_3d.nc"

OUTPUT_DIR = PROJECT_ROOT / "backend" / "data" / "physics"
OUTPUT_MEMBER_PATH = OUTPUT_DIR / "physics_adjusted_member_predictions.nc"
OUTPUT_STATS_PATH = OUTPUT_DIR / "physics_adjusted.nc"

BATCH_SIZE = 8  # Process 8 days at a time to prevent RAM exhaustion


def main() -> None:
    print("=" * 70)
    print("OceanEmbed — Physics Post-Processing (Chunked)")
    print("=" * 70)

    if not INPUT_PATH.exists():
        raise RuntimeError(f"Input file missing: {INPUT_PATH}")
    if not MASK_PATH.exists():
        raise RuntimeError(f"3D Mask missing: {MASK_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Load the Physical Valid Mask Contract
    # ------------------------------------------------------------------
    with xr.open_dataset(MASK_PATH) as ds_mask:
        var_name = "mask" if "mask" in ds_mask.data_vars else list(ds_mask.data_vars)[0]
    
        mask_3d = ds_mask[var_name].values.astype(bool) # Expected [15, lat, lon]
        n_depths, n_lat, n_lon = mask_3d.shape
        
    # Flatten spatial dims to [lat*lon, 15] to match the physics contract
    mask_flat = mask_3d.transpose(1, 2, 0).reshape(-1, n_depths)

    # ------------------------------------------------------------------
    # 2. Lazy-Load Input Data
    # ------------------------------------------------------------------
    ds_in = xr.open_dataset(INPUT_PATH)
    times = ds_in.time.values
    n_times = len(times)
    n_members = len(ds_in.member)

    print(f"Total Days to Process : {n_times}")
    print(f"Ensemble Members      : {n_members}")
    print(f"Batch Size            : {BATCH_SIZE} days")

    # ------------------------------------------------------------------
    # 3. Process in Memory-Safe Batches
    # ------------------------------------------------------------------
    for start_idx in range(0, n_times, BATCH_SIZE):
        end_idx = min(start_idx + BATCH_SIZE, n_times)
        batch_times = times[start_idx:end_idx]
        current_batch_size = len(batch_times)
        
        print(f"\nProcessing chunk {start_idx:04d} to {end_idx:04d}...")

        # Load ONLY this specific time chunk into memory
        ds_chunk = ds_in.isel(time=slice(start_idx, end_idx)).load()
        
        t_members_raw = ds_chunk["temperature"].values # [member, time, depth, lat, lon]
        s_members_raw = ds_chunk["salinity"].values
        
        t_adj_batch = np.empty_like(t_members_raw)
        s_adj_batch = np.empty_like(s_members_raw)
        
        # Tile the base mask to cover the current batch size: [batch * lat * lon, 15]
        mask_batch = np.tile(mask_flat, (current_batch_size, 1))

        # --- Adjust each member independently ---
        for m in range(n_members):
            # Transpose to [time, lat, lon, depth] and flatten to [time * lat * lon, depth]
            t_m_flat = t_members_raw[m].transpose(0, 2, 3, 1).reshape(-1, n_depths)
            s_m_flat = s_members_raw[m].transpose(0, 2, 3, 1).reshape(-1, n_depths)

            # 1. Pre-Adjustment Diagnostics
            pre_stats = calculate_inversion_statistics(t_m_flat, s_m_flat, mask_batch)

            # 2. Apply Convective Adjustment
            t_adj_flat, s_adj_flat, passes, touched = apply_convective_adjustment(
                t_m_flat, s_m_flat, mask_batch
            )

            # 3. Post-Adjustment Verification
            post_stats = calculate_inversion_statistics(t_adj_flat, s_adj_flat, mask_batch)

            print(
                f"  Member {m} | "
                f"Pre-adj Inv Col: {pre_stats['column_rate']:.2f}% | "
                f"Post-adj Inv Col: {post_stats['column_rate']:.2f}% | "
                f"Passes: {passes} | Touched: {touched:.2f}%"
            )

            # Convert to numpy for storage
            t_adj_flat = np.asarray(t_adj_flat)
            s_adj_flat = np.asarray(s_adj_flat)

            # Reshape back to [time, depth, lat, lon]
            t_adj_batch[m] = t_adj_flat.reshape(current_batch_size, n_lat, n_lon, n_depths).transpose(0, 3, 1, 2)
            s_adj_batch[m] = s_adj_flat.reshape(current_batch_size, n_lat, n_lon, n_depths).transpose(0, 3, 1, 2)

        # --- Compute Final Physics-Adjusted Statistics ---
        t_mean = np.mean(t_adj_batch, axis=0, dtype=np.float32)
        s_mean = np.mean(s_adj_batch, axis=0, dtype=np.float32)
        t_std = np.std(t_adj_batch, axis=0, ddof=0, dtype=np.float32)
        s_std = np.std(s_adj_batch, axis=0, ddof=0, dtype=np.float32)

        # ------------------------------------------------------------------
        # 4. Save Chunk to Disk
        # ------------------------------------------------------------------
        coords_stats = {
            "time": ds_chunk.time,
            "depth": ds_chunk.depth,
            "latitude": ds_chunk.latitude,
            "longitude": ds_chunk.longitude,
        }

        out_stats = xr.Dataset(
            {
                "temperature_mean": (("time", "depth", "latitude", "longitude"), t_mean),
                "salinity_mean": (("time", "depth", "latitude", "longitude"), s_mean),
                "temperature_std": (("time", "depth", "latitude", "longitude"), t_std),
                "salinity_std": (("time", "depth", "latitude", "longitude"), s_std),
            },
            coords=coords_stats,
            attrs={"convective_adjustment": "applied"}
        )
        
        out_members = xr.Dataset(
            {
                "temperature": (("member", "time", "depth", "latitude", "longitude"), t_adj_batch),
                "salinity": (("member", "time", "depth", "latitude", "longitude"), s_adj_batch),
            },
            coords={"member": ds_chunk.member, **coords_stats},
            attrs={"convective_adjustment": "applied"}
        )

        # Create a temporary directory for chunks
        chunk_dir = OUTPUT_DIR / "temp_chunks"
        chunk_dir.mkdir(parents=True, exist_ok=True)
        
        # Save individual chunks
        out_stats.to_netcdf(chunk_dir / f"stats_{start_idx:04d}.nc", engine="netcdf4")
        out_members.to_netcdf(chunk_dir / f"members_{start_idx:04d}.nc", engine="netcdf4")
        
        del ds_chunk, t_members_raw, s_members_raw, t_adj_batch, s_adj_batch, out_stats, out_members

    ds_in.close()

    # ------------------------------------------------------------------
    # 5. Merge Chunks into Final Files
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("Stitching chunks into final NetCDF files (Lazy-loading)...")
    
    # open_mfdataset streams the chunks without loading them entirely into memory
    final_stats = xr.open_mfdataset(str(chunk_dir / "stats_*.nc"), combine="by_coords")
    final_stats.to_netcdf(OUTPUT_STATS_PATH, engine="netcdf4")
    final_stats.close()
    
    final_members = xr.open_mfdataset(str(chunk_dir / "members_*.nc"), combine="by_coords")
    final_members.to_netcdf(OUTPUT_MEMBER_PATH, engine="netcdf4")
    final_members.close()

    # Clean up temp chunks
    for f in chunk_dir.glob("*.nc"):
        f.unlink()
    chunk_dir.rmdir()

    print("SUCCESS: Full ensemble adjusted and aggregated safely.")
    print(f"Final Stats Saved To: {OUTPUT_STATS_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    main()