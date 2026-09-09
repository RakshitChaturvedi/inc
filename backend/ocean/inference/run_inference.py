from __future__ import annotations

import json
from pathlib import Path
from netCDF4 import Dataset

import numpy as np
import torch
import xarray as xr

from .ensemble import run_ensemble_inference
from .model_loader import load_ensemble


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REGISTRY = PROJECT_ROOT / "model-registry" / "oceanembed-v1.0.0"

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "inference"
    / "input_tensor_normalized.nc"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "inference"
OUTPUT_PATH = OUTPUT_DIR / "ensemble_predictions.nc"
MEMBER_OUTPUT_PATH = OUTPUT_DIR / "ensemble_member_predictions.nc"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EXPECTED_CHANNELS = [
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

NUM_MEMBERS = 5
NUM_OUTPUT_DEPTHS = 15
LAT_SIZE = 101
LON_SIZE = 241


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_input() -> xr.Dataset:
    """Load and validate the inference input NetCDF."""

    print("=" * 70)
    print("OceanEmbed — Loading Inference Input")
    print("=" * 70)

    if not INPUT_PATH.exists():
        raise RuntimeError(f"Input file missing: {INPUT_PATH}")

    ds = xr.open_dataset(INPUT_PATH)

    if "input_tensor" not in ds:
        ds.close()
        raise RuntimeError(
            "Inference dataset does not contain 'input_tensor'"
        )

    tensor = ds["input_tensor"]

    expected_dims = (
        "time",
        "latitude",
        "longitude",
        "channel",
    )

    if tensor.dims != expected_dims:
        ds.close()
        raise RuntimeError(
            f"Unexpected tensor dimensions.\n"
            f"Expected: {expected_dims}\n"
            f"Actual:   {tensor.dims}"
        )

    expected_shape = (
        1419,
        LAT_SIZE,
        LON_SIZE,
        len(EXPECTED_CHANNELS),
    )

    if tensor.shape != expected_shape:
        ds.close()
        raise RuntimeError(
            f"Unexpected tensor shape.\n"
            f"Expected: {expected_shape}\n"
            f"Actual:   {tensor.shape}"
        )

    if tensor.dtype != np.float32:
        ds.close()
        raise RuntimeError(
            f"Expected float32 input, got {tensor.dtype}"
        )

    print(f"Input      : {INPUT_PATH}")
    print(f"Shape      : {tensor.shape}")
    print(f"Time range : {tensor.time.values[0]} -> "
          f"{tensor.time.values[-1]}")
    print("PASS")

    return ds


def get_device() -> torch.device:
    """Select CUDA when available, otherwise CPU."""

    if torch.cuda.is_available():
        device = torch.device("cuda")
        print(f"\nDevice: {torch.cuda.get_device_name(0)}")
    else:
        device = torch.device("cpu")
        print("\nDevice: CPU")

    return device

def create_member_output(
    times: np.ndarray,
    latitudes: np.ndarray,
    longitudes: np.ndarray,
    depths: np.ndarray,
):
    """Create disk-backed NetCDF for individual ensemble members."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if MEMBER_OUTPUT_PATH.exists():
        MEMBER_OUTPUT_PATH.unlink()

    nc = Dataset(
        MEMBER_OUTPUT_PATH,
        mode="w",
        format="NETCDF4",
    )

    # Dimensions
    nc.createDimension("member", NUM_MEMBERS)
    nc.createDimension("time", len(times))
    nc.createDimension("depth", NUM_OUTPUT_DEPTHS)
    nc.createDimension("latitude", LAT_SIZE)
    nc.createDimension("longitude", LON_SIZE)

    # Coordinates
    member_var = nc.createVariable(
        "member",
        "i4",
        ("member",),
    )

    time_var = nc.createVariable(
        "time",
        "f8",
        ("time",),
    )

    depth_var = nc.createVariable(
        "depth",
        "f4",
        ("depth",),
    )

    lat_var = nc.createVariable(
        "latitude",
        "f8",
        ("latitude",),
    )

    lon_var = nc.createVariable(
        "longitude",
        "f8",
        ("longitude",),
    )

    member_var[:] = np.arange(NUM_MEMBERS)
    depth_var[:] = depths
    lat_var[:] = latitudes
    lon_var[:] = longitudes

    # Convert datetime64 → numeric NetCDF time
    time_var.units = "days since 1970-01-01 00:00:00"
    time_var.calendar = "standard"

    time_numeric = (
        times.astype("datetime64[ns]").astype("int64")
        / 86_400_000_000_000
    )

    time_var[:] = time_numeric

    # Prediction variables
    temperature_var = nc.createVariable(
        "temperature",
        "f4",
        (
            "member",
            "time",
            "depth",
            "latitude",
            "longitude",
        ),
        zlib=True,
        complevel=4,
        chunksizes=(1, 1, NUM_OUTPUT_DEPTHS, LAT_SIZE, LON_SIZE),
    )

    salinity_var = nc.createVariable(
        "salinity",
        "f4",
        (
            "member",
            "time",
            "depth",
            "latitude",
            "longitude",
        ),
        zlib=True,
        complevel=4,
        chunksizes=(1, 1, NUM_OUTPUT_DEPTHS, LAT_SIZE, LON_SIZE),
    )

    nc.project = "OceanEmbed"
    nc.model = "OceanEmbed"
    nc.model_version = "production-v1"
    nc.ensemble_size = NUM_MEMBERS
    nc.artifact = "raw_ensemble_member_predictions"
    nc.convective_adjustment = "not_applied"
    nc.note = (
        "Individual ensemble-member predictions before "
        "convective adjustment and ensemble aggregation."
    )

    return nc, temperature_var, salinity_var

def save_predictions(
    times: np.ndarray,
    latitudes: np.ndarray,
    longitudes: np.ndarray,
    depths: np.ndarray,
    temperature_mean: np.ndarray,
    salinity_mean: np.ndarray,
    temperature_std: np.ndarray,
    salinity_std: np.ndarray,
) -> None:
    """Save final ensemble inference results to NetCDF."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output = xr.Dataset(
        data_vars={
            "temperature_mean": (
                ("time", "depth", "latitude", "longitude"),
                temperature_mean,
            ),
            "salinity_mean": (
                ("time", "depth", "latitude", "longitude"),
                salinity_mean,
            ),
            "temperature_std": (
                ("time", "depth", "latitude", "longitude"),
                temperature_std,
            ),
            "salinity_std": (
                ("time", "depth", "latitude", "longitude"),
                salinity_std,
            ),
        },
        coords={
            "time": times,
            "depth": depths,
            "latitude": latitudes,
            "longitude": longitudes,
        },
        attrs={
            "project": "OceanEmbed",
            "model": "OceanEmbed",
            "model_version": "production-v1",
            "ensemble_size": NUM_MEMBERS,
            "ensemble_method": "mean",
            "uncertainty_method": "ensemble_standard_deviation",
            "convective_adjustment": "not_applied",
            "note": (
                "Raw ensemble inference output. "
                "Convective adjustment is a subsequent post-processing step."
            ),
        },
    )

    encoding = {
        variable: {
            "dtype": "float32",
            "zlib": True,
            "complevel": 4,
        }
        for variable in output.data_vars
    }

    output.to_netcdf(
        OUTPUT_PATH,
        encoding=encoding,
    )

    output.close()

    print("\nOutput saved:")
    print(f"  {OUTPUT_PATH}")


# ---------------------------------------------------------------------------
# Main inference pipeline
# ---------------------------------------------------------------------------

def main() -> None:

    print("=" * 70)
    print("OceanEmbed — Full Ensemble Inference")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Load input
    # ------------------------------------------------------------------

    ds = load_input()

    tensor = ds["input_tensor"]

    times = ds["time"].values
    latitudes = ds["latitude"].values
    longitudes = ds["longitude"].values

    # ------------------------------------------------------------------
    # 2. Load ensemble
    # ------------------------------------------------------------------

    print("\nLoading ensemble...")

    device = get_device()

    models = load_ensemble(
        registry_root=REGISTRY,
        device=device,
    )

    if len(models) != NUM_MEMBERS:
        ds.close()
        raise RuntimeError(
            f"Expected {NUM_MEMBERS} ensemble members, "
            f"loaded {len(models)}"
        )

    for model in models:
        model.eval()

    print(f"Loaded {len(models)} ensemble members.")

    # ------------------------------------------------------------------
    # 3. Determine output depths
    # ------------------------------------------------------------------

    depths_path = REGISTRY / "depths.json"

    if not depths_path.exists():
        ds.close()
        raise RuntimeError(
            f"Missing depth metadata: {depths_path}\n"
            "Create depths.json in the model registry before inference."
        )

    with open(depths_path, "r", encoding="utf-8") as f:
        depth_metadata = json.load(f)

    if "target_depths_m" not in depth_metadata:
        ds.close()
        raise RuntimeError(
            "depths.json does not contain 'target_depths_m'"
        )

    depths = np.asarray(
        depth_metadata["target_depths_m"],
        dtype=np.float32,
    )

    if len(depths) != NUM_OUTPUT_DEPTHS:
        ds.close()
        raise RuntimeError(
            f"Expected {NUM_OUTPUT_DEPTHS} output depths, "
            f"got {len(depths)}"
        )

    print(f"Output depths: {depths.tolist()}")

    # ------------------------------------------------------------------
    # 4. Allocate final ensemble statistics
    # ------------------------------------------------------------------

    n_times = len(times)

    temperature_mean = np.empty(
        (n_times, NUM_OUTPUT_DEPTHS, LAT_SIZE, LON_SIZE),
        dtype=np.float32,
    )

    salinity_mean = np.empty(
        (n_times, NUM_OUTPUT_DEPTHS, LAT_SIZE, LON_SIZE),
        dtype=np.float32,
    )

    temperature_std = np.empty(
        (n_times, NUM_OUTPUT_DEPTHS, LAT_SIZE, LON_SIZE),
        dtype=np.float32,
    )

    salinity_std = np.empty(
        (n_times, NUM_OUTPUT_DEPTHS, LAT_SIZE, LON_SIZE),
        dtype=np.float32,
    )

    member_nc, member_temperature, member_salinity = (
        create_member_output(
            times=times,
            latitudes=latitudes,
            longitudes=longitudes,
            depths=depths,
        )
    )

    print(
        f"\nMember predictions will be written to:\n"
        f"  {MEMBER_OUTPUT_PATH}"
    )
    # ------------------------------------------------------------------
    # 5. Run inference
    # ------------------------------------------------------------------

    print("\n" + "=" * 70)
    print("Running ensemble inference")
    print("=" * 70)

    with torch.inference_mode():

        for time_index in range(n_times):

            # NetCDF:
            #   [latitude, longitude, channel]
            #
            # Model:
            #   [batch, channel, latitude, longitude]

            input_np = tensor.isel(time=time_index).values

            input_np = np.transpose(
                input_np,
                (2, 0, 1),
            )

            input_np = np.expand_dims(
                input_np,
                axis=0,
            )

            if input_np.shape != (
                1,
                len(EXPECTED_CHANNELS),
                LAT_SIZE,
                LON_SIZE,
            ):
                ds.close()
                raise RuntimeError(
                    f"Unexpected model input shape at time index "
                    f"{time_index}: {input_np.shape}"
                )

            # ----------------------------------------------------------
            # Ensemble forward pass
            # ----------------------------------------------------------

            t_members, s_members = run_ensemble_inference(
                models=models,
                input_array=input_np,
                device=device,
            )

            # ----------------------------------------------------------
            # Validate ensemble output
            # ----------------------------------------------------------

            expected_output_shape = (
                NUM_MEMBERS,
                NUM_OUTPUT_DEPTHS,
                LAT_SIZE,
                LON_SIZE,
            )

            if t_members.shape != expected_output_shape:
                ds.close()
                raise RuntimeError(
                    f"Unexpected temperature output shape at "
                    f"time index {time_index}: {t_members.shape}"
                )

            if s_members.shape != expected_output_shape:
                ds.close()
                raise RuntimeError(
                    f"Unexpected salinity output shape at "
                    f"time index {time_index}: {s_members.shape}"
                )
            # ----------------------------------------------------------
            # Persist individual ensemble members
            # ----------------------------------------------------------

            member_temperature[:, time_index, :, :, :] = (
                t_members.astype(np.float32)
            )

            member_salinity[:, time_index, :, :, :] = (
                s_members.astype(np.float32)
            )
            # ----------------------------------------------------------
            # Ensemble aggregation
            # ----------------------------------------------------------

            temperature_mean[time_index] = np.mean(
                t_members,
                axis=0,
                dtype=np.float32,
            )

            salinity_mean[time_index] = np.mean(
                s_members,
                axis=0,
                dtype=np.float32,
            )

            temperature_std[time_index] = np.std(
                t_members,
                axis=0,
                dtype=np.float32,
            )

            salinity_std[time_index] = np.std(
                s_members,
                axis=0,
                dtype=np.float32,
            )

            # ----------------------------------------------------------
            # Progress
            # ----------------------------------------------------------

            if (
                time_index == 0
                or (time_index + 1) % 25 == 0
                or time_index == n_times - 1
            ):
                print(
                    f"  [{time_index + 1:4d}/{n_times}] "
                    f"{times[time_index]}"
                )
            if (time_index + 1) % 10 == 0:
                member_nc.sync()

            # Explicitly release per-day member arrays.
            del t_members
            del s_members

            if device.type == "cuda":
                torch.cuda.empty_cache()

    # ------------------------------------------------------------------
    # 6. Close input
    # ------------------------------------------------------------------

    ds.close()
    member_nc.close()

    # ------------------------------------------------------------------
    # 7. Save results
    # ------------------------------------------------------------------

    save_predictions(
        times=times,
        latitudes=latitudes,
        longitudes=longitudes,
        depths=depths,
        temperature_mean=temperature_mean,
        salinity_mean=salinity_mean,
        temperature_std=temperature_std,
        salinity_std=salinity_std,
    )

    # ------------------------------------------------------------------
    # 8. Final summary
    # ------------------------------------------------------------------

    print("\n" + "=" * 70)
    print("INFERENCE COMPLETE")
    print("=" * 70)

    print(f"Days processed       : {n_times}")
    print(f"Ensemble members     : {NUM_MEMBERS}")
    print(f"Output depths        : {NUM_OUTPUT_DEPTHS}")
    print(f"Spatial grid         : {LAT_SIZE} × {LON_SIZE}")
    print(f"Temperature output   : {temperature_mean.shape}")
    print(f"Salinity output      : {salinity_mean.shape}")
    print(f"Temperature std      : {temperature_std.shape}")
    print(f"Salinity std         : {salinity_std.shape}")
    print(f"Output               : {OUTPUT_PATH}")
    print(f"Member predictions   : {MEMBER_OUTPUT_PATH}")
    print("Convective adjustment: NOT APPLIED")
    print("=" * 70)


if __name__ == "__main__":
    main()