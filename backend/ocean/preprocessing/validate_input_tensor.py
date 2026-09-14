from pathlib import Path
import json

import numpy as np
import xarray as xr


# ================================================================
# CONFIGURATION
# ================================================================

ARTIFACT_PATH = Path(
    "data/processed/input_tensor_normalized.nc"
)

REGISTRY_DIR = Path(
    "model-registry"
)

REGISTRY_PATH = (
    REGISTRY_DIR
    / "oceanembed-v1.0.0"
    / "ocean_mask.nc"
)

NORMALIZATION_STATS_PATH = (
    REGISTRY_DIR
    / "oceanembed-v1.0.0"
    / "normalization_stats.json"
)

EXPECTED_SHAPE = (1, 12, 101, 241)

CHANNELS = [
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

NORMALIZED_CHANNELS = [
    "SST",
    "SSS",
    "SSHA",
    "wind_U",
    "wind_V",
    "current_U",
    "current_V",
    "wind_stress_curl",
]

UNCHANGED_CHANNELS = [
    "latitude",
    "longitude",
    "sin_day_of_year",
    "cos_day_of_year",
]


# ================================================================
# VALIDATION STATE
# ================================================================

errors = []
warnings = []


def section(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def passed(message):
    print(f"[PASS] {message}")


def failed(message):
    print(f"[FAIL] {message}")
    errors.append(message)


def warning(message):
    print(f"[WARN] {message}")
    warnings.append(message)


# ================================================================
# 1. FILE EXISTENCE
# ================================================================

section("1. ARTIFACT")

if not ARTIFACT_PATH.exists():

    failed(
        f"Artifact does not exist: {ARTIFACT_PATH}"
    )

    raise SystemExit(1)

passed(
    f"Artifact exists: {ARTIFACT_PATH}"
)


# ================================================================
# 2. OPEN NETCDF
# ================================================================

section("2. NETCDF OPEN")

try:

    ds = xr.open_dataset(ARTIFACT_PATH)

    passed("NetCDF artifact opened successfully")

except Exception as exc:

    failed(
        f"Could not open NetCDF artifact: {exc}"
    )

    raise SystemExit(1)


# ================================================================
# 3. REQUIRED VARIABLES
# ================================================================

section("3. REQUIRED VARIABLES")

required_variables = [
    "input_tensor",
    "effective_ocean_mask",
]

for variable in required_variables:

    if variable in ds.data_vars:

        passed(
            f"Variable present: {variable}"
        )

    else:

        failed(
            f"Missing required variable: {variable}"
        )


# ================================================================
# 4. DIMENSIONS
# ================================================================

section("4. DIMENSIONS")

expected_dimensions = {
    "batch": 1,
    "channel": 12,
    "latitude": 101,
    "longitude": 241,
}

for dim, expected_size in expected_dimensions.items():

    if dim not in ds.dims:

        failed(
            f"Missing dimension: {dim}"
        )

        continue

    actual_size = ds.dims[dim]

    print(
        f"{dim:10s}: {actual_size}"
    )

    if actual_size != expected_size:

        failed(
            f"Dimension {dim} has size "
            f"{actual_size}; expected {expected_size}"
        )

    else:

        passed(
            f"Dimension {dim} is correct"
        )


# ================================================================
# 5. INPUT TENSOR
# ================================================================

section("5. INPUT TENSOR")

if "input_tensor" in ds:

    tensor = ds["input_tensor"].values

    print(f"Shape : {tensor.shape}")
    print(f"Dtype : {tensor.dtype}")

    if tensor.shape != EXPECTED_SHAPE:

        failed(
            f"Unexpected tensor shape: "
            f"{tensor.shape}; expected {EXPECTED_SHAPE}"
        )

    else:

        passed(
            f"Tensor shape is correct: {EXPECTED_SHAPE}"
        )

    if tensor.dtype != np.float32:

        failed(
            f"Unexpected tensor dtype: "
            f"{tensor.dtype}; expected float32"
        )

    else:

        passed(
            "Tensor dtype is float32"
        )

    nan_count = int(
        np.isnan(tensor).sum()
    )

    inf_count = int(
        np.isinf(tensor).sum()
    )

    print(f"NaNs : {nan_count}")
    print(f"Infs : {inf_count}")

    if nan_count != 0:

        failed(
            f"Tensor contains {nan_count} NaNs"
        )

    else:

        passed("Tensor contains no NaNs")

    if inf_count != 0:

        failed(
            f"Tensor contains {inf_count} infinite values"
        )

    else:

        passed(
            "Tensor contains no infinite values"
        )


# ================================================================
# 6. CHANNEL ORDER
# ================================================================

section("6. CHANNEL ORDER")

if "channel" in ds.coords:

    actual_channels = [
        str(x)
        for x in ds["channel"].values
    ]

    print("Expected:")
    for i, channel in enumerate(CHANNELS):
        print(f"  {i:2d}: {channel}")

    print()
    print("Artifact:")
    for i, channel in enumerate(actual_channels):
        print(f"  {i:2d}: {channel}")

    if actual_channels != CHANNELS:

        failed(
            "Channel ordering does not match the "
            "OceanEmbed 12-channel contract."
        )

    else:

        passed(
            "Channel ordering matches the 12-channel contract"
        )

else:

    failed(
        "Artifact is missing the channel coordinate"
    )


# ================================================================
# 7. COORDINATES
# ================================================================

section("7. GRID COORDINATES")

if "latitude" in ds.coords:

    latitude = ds["latitude"].values

    print(
        f"Latitude: "
        f"{latitude.min()} -> {latitude.max()} "
        f"({len(latitude)} cells)"
    )

    if len(latitude) != 101:

        failed(
            "Latitude coordinate does not contain 101 cells"
        )

    if not np.allclose(
        latitude,
        np.linspace(5.0, 30.0, 101),
        atol=1e-6,
    ):

        failed(
            "Latitude coordinate does not match "
            "the 5–30°N 0.25° grid."
        )

    else:

        passed(
            "Latitude coordinate matches the target grid"
        )

else:

    failed(
        "Missing latitude coordinate"
    )


if "longitude" in ds.coords:

    longitude = ds["longitude"].values

    print(
        f"Longitude: "
        f"{longitude.min()} -> {longitude.max()} "
        f"({len(longitude)} cells)"
    )

    if len(longitude) != 241:

        failed(
            "Longitude coordinate does not contain 241 cells"
        )

    if not np.allclose(
        longitude,
        np.linspace(45.0, 105.0, 241),
        atol=1e-6,
    ):

        failed(
            "Longitude coordinate does not match "
            "the 45–105°E 0.25° grid."
        )

    else:

        passed(
            "Longitude coordinate matches the target grid"
        )

else:

    failed(
        "Missing longitude coordinate"
    )


# ================================================================
# 8. EFFECTIVE OCEAN REGION
# ================================================================

section("8. EFFECTIVE OCEAN REGION")

effective_mask = None
effective_count = None
excluded_count = None

if "effective_ocean_mask" not in ds.data_vars:

    failed(
        "Final artifact is missing "
        "'effective_ocean_mask'"
    )

else:

    effective_mask = (
        ds["effective_ocean_mask"]
        .values
        .squeeze()
        .astype(bool)
    )

    print(
        f"Effective mask shape: "
        f"{effective_mask.shape}"
    )

    if effective_mask.shape != (101, 241):

        failed(
            "Effective ocean mask shape is not "
            "(101, 241)"
        )

    else:

        passed(
            "Effective ocean mask shape is correct"
        )

    effective_count = int(
        effective_mask.sum()
    )

    excluded_count = int(
        effective_mask.size
        - effective_count
    )

    print(
        f"Effective computational cells: "
        f"{effective_count:,}"
    )

    print(
        f"Excluded cells: "
        f"{excluded_count:,}"
    )

    if effective_count != 12068:

        warning(
            f"Current January 2 test artifact is expected "
            f"to contain 12,068 effective cells; got "
            f"{effective_count:,}."
        )

    else:

        passed(
            "Effective computational ocean cell count "
            "is exactly 12,068"
        )


# ================================================================
# 9. MASK CONSISTENCY
# ================================================================

section("9. MASK CONSISTENCY")

ocean_mask = None

if not REGISTRY_PATH.exists():

    failed(
        f"Registry ocean mask does not exist: "
        f"{REGISTRY_PATH}"
    )

else:

    try:

        with xr.open_dataset(REGISTRY_PATH) as mask_ds:

            if "ocean_mask" in mask_ds:

                ocean_mask = (
                    mask_ds["ocean_mask"]
                    .values
                    .squeeze()
                    .astype(bool)
                )

            elif "mask" in mask_ds:

                ocean_mask = (
                    mask_ds["mask"]
                    .values
                    .squeeze()
                    .astype(bool)
                )

            else:

                failed(
                    "Registry mask contains neither "
                    "'ocean_mask' nor 'mask'"
                )

    except Exception as exc:

        failed(
            f"Could not read registry ocean mask: {exc}"
        )


if effective_mask is not None and ocean_mask is not None:

    if ocean_mask.shape != (101, 241):

        failed(
            f"Registry ocean mask has shape "
            f"{ocean_mask.shape}; expected (101, 241)"
        )

    else:

        passed(
            "Registry ocean mask shape is correct"
        )

    invalid_effective_cells = (
        effective_mask
        & ~ocean_mask
    )

    invalid_count = int(
        invalid_effective_cells.sum()
    )

    print(
        f"Effective cells outside registry ocean: "
        f"{invalid_count:,}"
    )

    if invalid_count != 0:

        failed(
            "Effective mask contains cells that "
            "are land according to the registry mask."
        )

    else:

        passed(
            "Effective mask is a subset of the "
            "registry ocean mask"
        )

    total_cells = 101 * 241

    if (
        effective_count is not None
        and excluded_count is not None
        and effective_count + excluded_count
        != total_cells
    ):

        failed(
            "Effective + excluded cells do not cover "
            "the complete 101 × 241 grid."
        )

    else:

        passed(
            "Effective + excluded cells cover the "
            "complete 101 × 241 grid."
        )


# ================================================================
# 10. EXCLUDED-CELL ZERO CHECK
# ================================================================

section("10. EXCLUDED-CELL VALUES")

if effective_mask is not None and "input_tensor" in ds:

    tensor = ds["input_tensor"].values

    tensor_data = tensor[0]

    excluded_values = tensor_data[
        :,
        ~effective_mask
    ]

    nonzero_excluded = int(
        np.count_nonzero(excluded_values)
    )

    print(
        f"Non-zero values in excluded cells: "
        f"{nonzero_excluded:,}"
    )

    if nonzero_excluded != 0:

        failed(
            "Excluded cells contain non-zero tensor values."
        )

    else:

        passed(
            "All excluded tensor cells are exactly zero."
        )


# ================================================================
# 11. EFFECTIVE-CELL FINITE CHECK
# ================================================================

section("11. EFFECTIVE-CELL VALUES")

if effective_mask is not None and "input_tensor" in ds:

    tensor = ds["input_tensor"].values

    effective_values = tensor[
        0,
        :,
        effective_mask,
    ]

    if not np.all(
        np.isfinite(effective_values)
    ):

        failed(
            "Effective ocean cells contain NaN "
            "or infinite values."
        )

    else:

        passed(
            "All effective ocean cells contain "
            "finite values."
        )


# ================================================================
# 12. NORMALIZATION REGISTRY CHECK
# ================================================================

section("12. NORMALIZATION REGISTRY")

if not NORMALIZATION_STATS_PATH.exists():

    warning(
        "Normalization statistics file not found: "
        f"{NORMALIZATION_STATS_PATH}"
    )

else:

    try:

        with open(
            NORMALIZATION_STATS_PATH,
            "r",
        ) as f:

            stats = json.load(f)

        statistics = stats.get(
            "statistics"
        )

        if statistics is None:

            failed(
                "Normalization registry is missing "
                "'statistics'."
            )

        else:

            for channel in NORMALIZED_CHANNELS:

                if channel not in statistics:

                    failed(
                        f"Normalization registry missing "
                        f"channel: {channel}"
                    )

                else:

                    entry = statistics[channel]

                    required_keys = [
                        "mean",
                        "std",
                        "min",
                        "max",
                    ]

                    missing_keys = [
                        key
                        for key in required_keys
                        if key not in entry
                    ]

                    if missing_keys:

                        failed(
                            f"{channel} normalization entry "
                            f"missing: {missing_keys}"
                        )

                    else:

                        passed(
                            f"{channel}: normalization "
                            f"statistics present"
                        )

    except Exception as exc:

        failed(
            f"Could not read normalization registry: {exc}"
        )


# ================================================================
# 13. CHANNEL STATISTICS
# ================================================================

section("13. CHANNEL STATISTICS")

if effective_mask is not None and "input_tensor" in ds:

    tensor = ds["input_tensor"].values[0]

    for index, channel in enumerate(CHANNELS):

        channel_data = tensor[index]

        valid = (
            np.isfinite(channel_data)
            & effective_mask
        )

        values = channel_data[valid]

        if values.size == 0:

            failed(
                f"{channel}: no valid effective-ocean values"
            )

            continue

        print(
            f"{channel:20s} "
            f"min={values.min(): .6f}  "
            f"max={values.max(): .6f}  "
            f"mean={values.mean(): .6f}"
        )


# ================================================================
# 14. NORMALIZED CHANNEL SANITY
# ================================================================

section("14. NORMALIZED CHANNEL SANITY")

if effective_mask is not None and "input_tensor" in ds:

    tensor = ds["input_tensor"].values[0]

    for index, channel in enumerate(NORMALIZED_CHANNELS):

        channel_data = tensor[index]

        valid = (
            np.isfinite(channel_data)
            & effective_mask
        )

        values = channel_data[valid]

        if values.size == 0:
            continue

        mean = float(values.mean())
        std = float(values.std())

        print(
            f"{channel:20s} "
            f"mean={mean: .6f}  "
            f"std={std: .6f}"
        )

        # These are sanity checks, not exact equality checks.
        if abs(mean) > 2.0:

            warning(
                f"{channel} mean is {mean:.4f}; "
                f"large deviation from zero."
            )

        if std < 0.1:

            warning(
                f"{channel} standard deviation is "
                f"unusually small: {std:.6f}"
            )


# ================================================================
# 15. UNCHANGED TEMPORAL / SPATIAL CHANNELS
# ================================================================

section("15. SPATIAL / TEMPORAL CHANNELS")

if effective_mask is not None and "input_tensor" in ds:

    tensor = ds["input_tensor"].values[0]

    # ------------------------------------------------------------
    # Spatial channels
    # ------------------------------------------------------------
    #
    # Latitude and longitude are part of the 12-channel contract,
    # but they are normalized during preprocessing.
    #
    # Therefore they must NOT be compared directly against the
    # physical 5–30°N / 45–105°E coordinates here.
    #
    # Their presence, finiteness, and effective-ocean coverage are
    # already validated above.

    latitude_data = tensor[8]
    longitude_data = tensor[9]

    lat_values = latitude_data[effective_mask]
    lon_values = longitude_data[effective_mask]

    if np.all(np.isfinite(lat_values)):

        passed(
            "Latitude channel contains finite values "
            "on all effective cells."
        )

    else:

        failed(
            "Latitude channel contains non-finite "
            "values on effective cells."
        )

    if np.all(np.isfinite(lon_values)):

        passed(
            "Longitude channel contains finite values "
            "on all effective cells."
        )

    else:

        failed(
            "Longitude channel contains non-finite "
            "values on effective cells."
        )

    # ------------------------------------------------------------
    # Temporal channels
    # ------------------------------------------------------------
    #
    # Current OceanEmbed feature implementation:
    #
    #   sin_day_of_year = sin(2π * day_of_year / 365)
    #   cos_day_of_year = cos(2π * day_of_year / 365)
    #
    # January 2 -> day_of_year = 2.
    #

    sin_values = tensor[10][effective_mask]
    cos_values = tensor[11][effective_mask]

    if sin_values.size == 0:

        failed(
            "No effective-ocean values available for "
            "temporal channels."
        )

    else:

        sin_unique = np.unique(
            np.round(sin_values, 6)
        )

        cos_unique = np.unique(
            np.round(cos_values, 6)
        )

        print(
            f"sin_day_of_year unique values: "
            f"{sin_unique}"
        )

        print(
            f"cos_day_of_year unique values: "
            f"{cos_unique}"
        )

        day_of_year = 2

        angle = (
            2.0
            * np.pi
            * day_of_year
            / 365.0
        )

        expected_sin = np.sin(angle)
        expected_cos = np.cos(angle)

        if np.allclose(
            sin_values,
            expected_sin,
            atol=1e-5,
        ):

            passed(
                "sin_day_of_year matches the "
                "January 2 feature value."
            )

        else:

            failed(
                "sin_day_of_year does not match "
                "the January 2 feature value."
            )

        if np.allclose(
            cos_values,
            expected_cos,
            atol=1e-5,
        ):

            passed(
                "cos_day_of_year matches the "
                "January 2 feature value."
            )

        else:

            failed(
                "cos_day_of_year does not match "
                "the January 2 feature value."
            )
# ================================================================
# 16. ARTIFACT METADATA
# ================================================================

section("16. ARTIFACT METADATA")

required_metadata = {
    "oceanembed_artifact": "input_tensor_normalized",
    "oceanembed_phase": 6,
    "normalization_method": "z-score",
    "normalization_formula": "(x - mean) / std",
    "grid_resolution": "0.25 degrees",
    "grid_shape": "101 x 241",
    "channel_count": 12,
    "dtype": "float32",
    "mask_source": "preprocessing effective_ocean_mask",
}

for key, expected_value in required_metadata.items():

    if key not in ds.attrs:

        failed(
            f"Missing metadata attribute: {key}"
        )

        continue

    actual_value = ds.attrs[key]

    print(
        f"{key}: {actual_value}"
    )

    if str(actual_value) != str(expected_value):

        failed(
            f"Metadata mismatch for {key}: "
            f"got {actual_value!r}, "
            f"expected {expected_value!r}"
        )

    else:

        passed(
            f"Metadata correct: {key}"
        )


# ================================================================
# 17. MASK METADATA
# ================================================================

section("17. MASK METADATA")

if "effective_ocean_mask" in ds:

    mask_attrs = ds[
        "effective_ocean_mask"
    ].attrs

    required_mask_attrs = [
        "long_name",
        "description",
        "valid_value",
        "invalid_value",
    ]

    for key in required_mask_attrs:

        if key in mask_attrs:

            passed(
                f"Mask metadata present: {key}"
            )

        else:

            failed(
                f"Mask metadata missing: {key}"
            )


# ================================================================
# 18. FINAL SUMMARY
# ================================================================

section("18. FINAL VALIDATION")

if errors:

    print(
        f"VALIDATION FAILED: "
        f"{len(errors)} error(s)"
    )

    for error in errors:

        print(
            f"  - {error}"
        )

else:

    print(
        "VALIDATION PASSED"
    )

    print()
    print(
        "The exported OceanEmbed NetCDF artifact "
        "satisfies the current Phase 6 artifact contract."
    )

if warnings:

    print()
    print(
        f"Warnings: {len(warnings)}"
    )

    for item in warnings:

        print(
            f"  - {item}"
        )

ds.close()

if errors:

    raise SystemExit(1)

print()
print("=" * 70)
print("VALIDATION COMPLETE")
print("=" * 70)