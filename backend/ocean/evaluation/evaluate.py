import json
import numpy as np
import xarray as xr
from datetime import datetime, timezone
from pathlib import Path

from ocean.evaluation.depth_metrics import calculate_all_depth_metrics
from ocean.evaluation.spatial_metrics import (
    initialize_spatial_accumulators,
    update_spatial_accumulators,
    finalize_spatial_metrics
)
from ocean.evaluation.uncertainty_metrics import (
    initialize_uncertainty_accumulators,
    update_uncertainty_accumulators,
    finalize_uncertainty_metrics
)
from ocean.evaluation.physics_metrics import calculate_physics_metrics

# Paths (Assuming execution from backend root)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_DIR = PROJECT_ROOT / "data" / "evaluation"
PREDICTION_PATH = PROJECT_ROOT / "data" / "physics" / "physics_adjusted.nc"
RAW_PREDICTION_PATH = PROJECT_ROOT / "data" / "inference" / "ensemble_member_predictions.nc"
TEMP_TARGET_PATH = EVALUATION_DIR / "temperature_targets_masked.nc"
SALT_TARGET_PATH = EVALUATION_DIR / "salinity_targets_masked.nc"
OCEAN_MASK_PATH = PROJECT_ROOT / "model-registry" / "oceanembed-v1.0.0" / "ocean_mask_3d.nc"
REPORT_PATH = EVALUATION_DIR / "evaluation_report.json"
BATCH_SIZE = 8

def main():
    print("=" * 70)
    print("OceanEmbed — Final Evaluation Pipeline")
    print("=" * 70)

    # 1. Open Datasets
    ds_pred = xr.open_dataset(PREDICTION_PATH)
    ds_raw = xr.open_dataset(RAW_PREDICTION_PATH)
    ds_temp_gt = xr.open_dataset(TEMP_TARGET_PATH)
    ds_salt_gt = xr.open_dataset(SALT_TARGET_PATH)
    
    n_times = ds_pred.sizes["time"]
    n_lat = ds_pred.sizes["latitude"]
    n_lon = ds_pred.sizes["longitude"]

    # 2. Initialize Accumulators
    print("Initializing metric accumulators...")
    spatial_acc = initialize_spatial_accumulators(n_lat, n_lon)
    uncert_acc = initialize_uncertainty_accumulators(20)
    bin_edges = np.linspace(0, 1.5, 21) # 20 bins for uncertainty standard deviations

    # 3. Chunked Streaming Loop
    print(f"Streaming {n_times} days for spatial and uncertainty metrics...")
    for start_idx in range(0, n_times, BATCH_SIZE):
        end_idx = min(start_idx + BATCH_SIZE, n_times)
        
        # Load Batch
        pred_batch = (
            ds_pred
            .isel(time=slice(start_idx, end_idx))
            .load()
        )

        t_gt_batch = (
            ds_temp_gt
            .isel(time=slice(start_idx, end_idx))
            .load()
        )

        s_gt_batch = (
            ds_salt_gt
            .isel(time=slice(start_idx, end_idx))
            .load()
        )

        # ------------------------------------------------------------------
        # Normalize all evaluation arrays to:
        # (time, depth, latitude, longitude)
        # ------------------------------------------------------------------

        t_pred = (
            pred_batch["temperature_mean"]
            .transpose("time", "depth", "latitude", "longitude")
            .values
        )

        s_pred = (
            pred_batch["salinity_mean"]
            .transpose("time", "depth", "latitude", "longitude")
            .values
        )

        t_std = (
            pred_batch["temperature_std"]
            .transpose("time", "depth", "latitude", "longitude")
            .values
        )

        s_std = (
            pred_batch["salinity_std"]
            .transpose("time", "depth", "latitude", "longitude")
            .values
        )

        t_truth = (
            t_gt_batch["temperature"]
            .transpose("time", "depth", "latitude", "longitude")
            .values
        )

        s_truth = (
            s_gt_batch["salinity"]
            .transpose("time", "depth", "latitude", "longitude")
            .values
        )

        # Sanity check
        assert t_pred.shape == t_truth.shape, (
            f"Temperature shape mismatch: "
            f"prediction={t_pred.shape}, truth={t_truth.shape}"
        )

        assert s_pred.shape == s_truth.shape, (
            f"Salinity shape mismatch: "
            f"prediction={s_pred.shape}, truth={s_truth.shape}"
        )

        # Update Spatial
        update_spatial_accumulators(
            spatial_acc,
            t_pred,
            t_truth,
            s_pred,
            s_truth,
        )

        # Update Uncertainty
        update_uncertainty_accumulators(
            uncert_acc,
            t_pred,
            t_truth,
            t_std,
            "temperature",
            bin_edges,
        )

        update_uncertainty_accumulators(
            uncert_acc,
            s_pred,
            s_truth,
            s_std,
            "salinity",
            bin_edges,
        )

    # 4. Finalize Chunked Metrics
    print("Finalizing accumulated metrics...")
    spatial_results = finalize_spatial_metrics(spatial_acc)
    uncert_results = finalize_uncertainty_metrics(uncert_acc, bin_edges)

    # Summarize spatial metrics for the JSON report (Global Mean)
    temp_spatial_mean_rmse = float(np.nanmean(spatial_results["temperature"]["rmse"]))
    salt_spatial_mean_rmse = float(np.nanmean(spatial_results["salinity"]["rmse"]))

    # 5. Depth and Physics Metrics
    print("Calculating Depth Metrics...")
    depth_results = calculate_all_depth_metrics(ds_pred, ds_temp_gt, ds_salt_gt, depths=[0.0, 5.0, 100.0, 1000.0])

    print("Calculating Physics Metrics...")
    # NOTE: Physics metrics loads the whole dataset arrays. For 1.1GB this fits in RAM safely.
    # We pass the ensemble mean of the raw predictions to evaluate the pre/post physics state
    physics_results = calculate_physics_metrics(
        raw_ds=ds_raw,
        adjusted_ds=ds_pred,
        batch_size=BATCH_SIZE,
    )

    # 6. Export JSON Report
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_shape": {"time": n_times, "lat": n_lat, "lon": n_lon},
        "depth_metrics": depth_results,
        "spatial_metrics_summary": {
            "temperature_global_mean_rmse": temp_spatial_mean_rmse,
            "salinity_global_mean_rmse": salt_spatial_mean_rmse
        },
        "uncertainty_metrics": uncert_results,
        "physics_metrics": physics_results
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=4)

    print(f"\nSUCCESS: Evaluation report generated at {REPORT_PATH}")

if __name__ == "__main__":
    main()