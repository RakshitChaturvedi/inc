from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import xarray as xr


ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    ROOT
    / "data"
    / "inference"
    / "input_tensor_normalized.nc"
)

REGISTRY = ROOT / "model-registry" / "oceanembed-v1.0.0"


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

EXPECTED_SHAPE = (1419, 101, 241, 12)

EXPECTED_DEPTHS = [
    0,
    5,
    10,
    20,
    30,
    50,
    75,
    100,
    125,
    150,
    200,
    300,
    500,
    700,
    1000,
]


def fail(message: str) -> None:
    raise RuntimeError(f"\nINPUT VALIDATION FAILED\n{message}")


def main() -> None:
    print("=" * 70)
    print("OceanEmbed — Inference Input Validation")
    print("=" * 70)

    if not INPUT_PATH.exists():
        fail(f"Input file does not exist:\n{INPUT_PATH}")

    print(f"\nInput: {INPUT_PATH}")

    with xr.open_dataset(INPUT_PATH) as ds:
        print("\nDataset:")
        print(ds)

        if len(ds.data_vars) == 0:
            fail("No data variables found.")

        # Find the actual tensor variable.
        if "input_tensor" in ds.data_vars:
            variable = ds["input_tensor"]
        elif len(ds.data_vars) == 1:
            variable = ds[next(iter(ds.data_vars))]
        else:
            fail(
                "Could not determine input tensor variable. "
                f"Variables found: {list(ds.data_vars)}"
            )

        print(f"\nTensor variable: {variable.name}")
        print(f"Dimensions: {variable.dims}")
        print(f"Shape: {variable.shape}")

        if tuple(variable.shape) != EXPECTED_SHAPE:
            fail(
                f"Unexpected tensor shape.\n"
                f"Expected: {EXPECTED_SHAPE}\n"
                f"Actual:   {tuple(variable.shape)}"
            )

        print("PASS: tensor shape")

        if not np.issubdtype(variable.dtype, np.floating):
            fail(f"Tensor must contain floating-point values. Got {variable.dtype}")

        print("PASS: tensor dtype")

        values = variable.values

        if not np.isfinite(values).all():
            bad = np.size(values) - np.isfinite(values).sum()
            fail(f"Tensor contains {bad} non-finite values.")

        print("PASS: tensor contains only finite values")

        # Validate channel metadata if present.
        channel_names = None

        for key in ("channel", "channels", "channel_name", "channel_names"):
            if key in ds.coords:
                channel_names = [
                    str(x) for x in ds.coords[key].values.tolist()
                ]
                break

        if channel_names is not None:
            if channel_names != EXPECTED_CHANNELS:
                fail(
                    "Channel order mismatch.\n"
                    f"Expected: {EXPECTED_CHANNELS}\n"
                    f"Actual:   {channel_names}"
                )

            print("PASS: channel ordering")

        # Validate time dimension.
        if "time" not in ds.coords:
            fail("No 'time' coordinate found.")

        times = ds["time"].values

        print(
            f"\nTime range:\n"
            f"  {times[0]}\n"
            f"  {times[-1]}"
        )

        if len(times) != 1419:
            fail(f"Expected 1419 timesteps, found {len(times)}")

        if not np.all(np.diff(times) > np.timedelta64(0, "s")):
            fail("Time coordinate is not strictly increasing.")

        print("PASS: time coordinate")

    # Validate registry contracts.
    channels_path = REGISTRY / "channels.json"
    depths_path = REGISTRY / "depths.json"
    normalization_path = REGISTRY / "normalization_stats.json"
    mask_path = REGISTRY / "ocean_mask.nc"
    mask3d_path = REGISTRY / "ocean_mask_3d.nc"

    for path in [
        channels_path,
        depths_path,
        normalization_path,
        mask_path,
        mask3d_path,
    ]:
        if not path.exists():
            fail(f"Required registry artifact missing:\n{path}")

    print("\nPASS: registry artifacts exist")

    with channels_path.open() as f:
        channels = json.load(f)

    registry_channels = [
        item["name"]
        for item in channels["channels"]
    ]

    if registry_channels != EXPECTED_CHANNELS:
        fail(
            "channels.json does not match expected channel contract.\n"
            f"Expected: {EXPECTED_CHANNELS}\n"
            f"Actual:   {registry_channels}"
        )

    print("PASS: channels.json")

    with depths_path.open() as f:
        depths = json.load(f)

    if depths["depths_m"] != EXPECTED_DEPTHS:
        fail(
            "depths.json does not match expected output depths.\n"
            f"Expected: {EXPECTED_DEPTHS}\n"
            f"Actual:   {depths['depths_m']}"
        )

    print("PASS: depths.json")

    print("\n" + "=" * 70)
    print("INPUT VALIDATION PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()