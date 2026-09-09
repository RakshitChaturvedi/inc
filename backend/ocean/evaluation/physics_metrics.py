from __future__ import annotations

from typing import Any

import numpy as np
import xarray as xr


PHYSICS_BATCH_SIZE = 8


def _safe_reduction(
    raw_value: float,
    adjusted_value: float,
) -> float:
    """
    Percentage reduction from raw -> adjusted.

    Positive = improvement
    Zero     = no change
    Negative = degradation
    """

    if raw_value == 0.0:
        return 0.0

    return float(
        (raw_value - adjusted_value)
        / raw_value
        * 100.0
    )


def _calculate_inversion_statistics(
    temperature: np.ndarray,
    salinity: np.ndarray,
    valid_mask: np.ndarray,
    density_alpha: float = 0.2,
    density_beta: float = 0.8,
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    """
    Calculate inversion statistics for one in-memory time batch.

    Expected shape:

        (time, depth, latitude, longitude)
    """

    t = np.asarray(temperature, dtype=np.float32)
    s = np.asarray(salinity, dtype=np.float32)
    mask = np.asarray(valid_mask, dtype=bool)

    if t.shape != s.shape:
        raise ValueError(
            f"Temperature and salinity shapes differ: "
            f"{t.shape} vs {s.shape}"
        )

    if t.shape != mask.shape:
        raise ValueError(
            f"Prediction and mask shapes differ: "
            f"{t.shape} vs {mask.shape}"
        )

    density = (
        density_alpha * (-t)
        + density_beta * s
    )

    delta_rho = (
        density[:, 1:, :, :]
        - density[:, :-1, :, :]
    )

    valid_transitions = (
        mask[:, 1:, :, :]
        & mask[:, :-1, :, :]
        & np.isfinite(delta_rho)
    )

    inversion = (
        (delta_rho < -tolerance)
        & valid_transitions
    )

    total_pairs = int(valid_transitions.sum())
    inversion_count = int(inversion.sum())

    layer_rate = (
        inversion_count / total_pairs * 100.0
        if total_pairs > 0
        else 0.0
    )

    valid_columns = valid_transitions.any(axis=1)
    inverted_columns = inversion.any(axis=1)

    total_valid_columns = int(valid_columns.sum())

    inverted_valid_columns = int(
        (inverted_columns & valid_columns).sum()
    )

    column_rate = (
        inverted_valid_columns
        / total_valid_columns
        * 100.0
        if total_valid_columns > 0
        else 0.0
    )

    inversion_magnitudes = np.abs(
        delta_rho[inversion]
    )

    aggregate_severity = (
        float(inversion_magnitudes.sum() / total_pairs)
        if total_pairs > 0
        else 0.0
    )

    return {
        "layer_rate_percent": float(layer_rate),
        "column_rate_percent": float(column_rate),
        "aggregate_severity": aggregate_severity,
        "inversion_count": inversion_count,
        "valid_transition_count": total_pairs,
        "inverted_column_count": inverted_valid_columns,
        "valid_column_count": total_valid_columns,
    }


def _initialize_stats() -> dict[str, float]:
    return {
        "inversion_count": 0,
        "valid_transition_count": 0,
        "inverted_column_count": 0,
        "valid_column_count": 0,
        "severity_sum": 0.0,
    }


def _accumulate_stats(
    accumulator: dict[str, float],
    stats: dict[str, Any],
) -> None:

    accumulator["inversion_count"] += stats[
        "inversion_count"
    ]

    accumulator["valid_transition_count"] += stats[
        "valid_transition_count"
    ]

    accumulator["inverted_column_count"] += stats[
        "inverted_column_count"
    ]

    accumulator["valid_column_count"] += stats[
        "valid_column_count"
    ]

    # Reconstruct severity numerator.
    #
    # aggregate_severity =
    #     inversion_magnitude_sum / valid_transition_count
    #
    # Therefore:
    #
    # magnitude_sum =
    #     aggregate_severity * valid_transition_count

    accumulator["severity_sum"] += (
        stats["aggregate_severity"]
        * stats["valid_transition_count"]
    )


def _finalize_stats(
    accumulator: dict[str, float],
) -> dict[str, Any]:

    total_pairs = int(
        accumulator["valid_transition_count"]
    )

    inversion_count = int(
        accumulator["inversion_count"]
    )

    total_columns = int(
        accumulator["valid_column_count"]
    )

    inverted_columns = int(
        accumulator["inverted_column_count"]
    )

    layer_rate = (
        inversion_count
        / total_pairs
        * 100.0
        if total_pairs > 0
        else 0.0
    )

    column_rate = (
        inverted_columns
        / total_columns
        * 100.0
        if total_columns > 0
        else 0.0
    )

    aggregate_severity = (
        accumulator["severity_sum"]
        / total_pairs
        if total_pairs > 0
        else 0.0
    )

    return {
        "layer_rate_percent": float(layer_rate),
        "column_rate_percent": float(column_rate),
        "aggregate_severity": float(aggregate_severity),
        "inversion_count": inversion_count,
        "valid_transition_count": total_pairs,
        "inverted_column_count": inverted_columns,
        "valid_column_count": total_columns,
    }


def calculate_physics_metrics(
    raw_ds: xr.Dataset,
    adjusted_ds: xr.Dataset,
    ocean_mask: xr.DataArray | None = None,
    batch_size: int = PHYSICS_BATCH_SIZE,
) -> dict[str, Any]:
    """
    Evaluate the effect of convective adjustment using
    memory-safe streaming over time.

    raw_ds may contain either:

        temperature / salinity

    or:

        temperature_mean / salinity_mean

    adjusted_ds is expected to contain:

        temperature_mean / salinity_mean
    """

    # ---------------------------------------------------------------
    # Resolve variable names
    # ---------------------------------------------------------------

    if "temperature_mean" in raw_ds:
        raw_temperature = raw_ds["temperature_mean"]
    elif "temperature" in raw_ds:
        raw_temperature = raw_ds["temperature"]
    else:
        raise ValueError(
            "Raw dataset missing temperature variable. "
            "Expected 'temperature_mean' or 'temperature'."
        )

    if "salinity_mean" in raw_ds:
        raw_salinity = raw_ds["salinity_mean"]
    elif "salinity" in raw_ds:
        raw_salinity = raw_ds["salinity"]
    else:
        raise ValueError(
            "Raw dataset missing salinity variable. "
            "Expected 'salinity_mean' or 'salinity'."
        )

    if "temperature_mean" not in adjusted_ds:
        raise ValueError(
            "Adjusted dataset missing 'temperature_mean'."
        )

    if "salinity_mean" not in adjusted_ds:
        raise ValueError(
            "Adjusted dataset missing 'salinity_mean'."
        )

    adjusted_temperature = adjusted_ds[
        "temperature_mean"
    ]

    adjusted_salinity = adjusted_ds[
        "salinity_mean"
    ]

    # ---------------------------------------------------------------
    # Coordinate contract
    # ---------------------------------------------------------------

    required_dims = [
        "time",
        "depth",
        "latitude",
        "longitude",
    ]

    for dim in required_dims:

        if dim not in raw_ds.dims:
            raise ValueError(
                f"Raw dataset missing dimension: {dim}"
            )

        if dim not in adjusted_ds.dims:
            raise ValueError(
                f"Adjusted dataset missing dimension: {dim}"
            )

        if raw_ds.sizes[dim] != adjusted_ds.sizes[dim]:
            raise ValueError(
                f"Dimension mismatch for {dim}: "
                f"{raw_ds.sizes[dim]} vs "
                f"{adjusted_ds.sizes[dim]}"
            )

    n_times = raw_ds.sizes["time"]

    # ---------------------------------------------------------------
    # Prepare mask
    # ---------------------------------------------------------------

    if ocean_mask is not None:

        mask = ocean_mask.astype(bool)

        expected_dims = {
            "depth",
            "latitude",
            "longitude",
        }

        if set(mask.dims) != expected_dims:
            raise ValueError(
                "3-D ocean mask must contain dimensions "
                "depth, latitude, longitude."
            )

        # Only materialize the small 3-D mask.
        mask_values = mask.values

    else:

        mask_values = None

    # ---------------------------------------------------------------
    # Accumulators
    # ---------------------------------------------------------------

    raw_acc = _initialize_stats()
    adjusted_acc = _initialize_stats()

    adjusted_cell_count = 0
    valid_cell_count = 0

    # ---------------------------------------------------------------
    # Streaming time batches
    # ---------------------------------------------------------------

    print(
        f"  Physics streaming: "
        f"{n_times} days in batches of {batch_size}"
    )

    for start_idx in range(
        0,
        n_times,
        batch_size,
    ):

        end_idx = min(
            start_idx + batch_size,
            n_times,
        )

        print(
            f"    Batch "
            f"{start_idx:04d}:{end_idx:04d}"
        )

        raw_t = (
            raw_temperature
            .isel(time=slice(start_idx, end_idx))
            .mean(dim="member")
            .transpose(
                "time",
                "depth",
                "latitude",
                "longitude",
            )
            .values
        )

        raw_s = (
            raw_salinity
            .isel(time=slice(start_idx, end_idx))
            .mean(dim="member")
            .transpose(
                "time",
                "depth",
                "latitude",
                "longitude",
            )
            .values
        )

        adj_t = (
            adjusted_temperature
            .isel(time=slice(start_idx, end_idx))
            .transpose(
                "time",
                "depth",
                "latitude",
                "longitude",
            )
            .values
        )

        adj_s = (
            adjusted_salinity
            .isel(time=slice(start_idx, end_idx))
            .transpose(
                "time",
                "depth",
                "latitude",
                "longitude",
            )
            .values
        )

        current_batch_size = end_idx - start_idx

        # -----------------------------------------------------------
        # Validity mask
        # -----------------------------------------------------------

        if mask_values is not None:

            valid_mask = np.broadcast_to(
                mask_values,
                (
                    current_batch_size,
                    *mask_values.shape,
                ),
            )

        else:

            valid_mask = (
                np.isfinite(raw_t)
                & np.isfinite(raw_s)
            )

        # -----------------------------------------------------------
        # Raw statistics
        # -----------------------------------------------------------

        raw_stats = _calculate_inversion_statistics(
            raw_t,
            raw_s,
            valid_mask,
        )

        _accumulate_stats(
            raw_acc,
            raw_stats,
        )

        # -----------------------------------------------------------
        # Adjusted statistics
        # -----------------------------------------------------------

        adjusted_stats = _calculate_inversion_statistics(
            adj_t,
            adj_s,
            valid_mask,
        )

        _accumulate_stats(
            adjusted_acc,
            adjusted_stats,
        )

        # -----------------------------------------------------------
        # Adjustment fraction
        # -----------------------------------------------------------

        changed = (
            ~np.isclose(
                raw_t,
                adj_t,
                rtol=0.0,
                atol=1e-7,
                equal_nan=True,
            )
            |
            ~np.isclose(
                raw_s,
                adj_s,
                rtol=0.0,
                atol=1e-7,
                equal_nan=True,
            )
        )

        changed &= valid_mask

        valid_cell_count += int(
            valid_mask.sum()
        )

        adjusted_cell_count += int(
            changed.sum()
        )

        # Release batch references explicitly.
        del raw_t
        del raw_s
        del adj_t
        del adj_s
        del valid_mask

    # ---------------------------------------------------------------
    # Finalize
    # ---------------------------------------------------------------

    raw_stats = _finalize_stats(raw_acc)
    adjusted_stats = _finalize_stats(adjusted_acc)

    inversion_layer_reduction = _safe_reduction(
        raw_stats["layer_rate_percent"],
        adjusted_stats["layer_rate_percent"],
    )

    inversion_column_reduction = _safe_reduction(
        raw_stats["column_rate_percent"],
        adjusted_stats["column_rate_percent"],
    )

    severity_reduction = _safe_reduction(
        raw_stats["aggregate_severity"],
        adjusted_stats["aggregate_severity"],
    )

    adjustment_fraction = (
        adjusted_cell_count
        / valid_cell_count
        * 100.0
        if valid_cell_count > 0
        else 0.0
    )

    return {
        "raw": raw_stats,

        "adjusted": adjusted_stats,

        "reduction": {
            "inversion_layer_reduction_percent":
                inversion_layer_reduction,

            "inversion_column_reduction_percent":
                inversion_column_reduction,

            "aggregate_severity_reduction_percent":
                severity_reduction,
        },

        "adjustment": {
            "adjusted_cell_count":
                int(adjusted_cell_count),

            "valid_cell_count":
                int(valid_cell_count),

            "adjustment_fraction_percent":
                float(adjustment_fraction),
        },

        "physics_success": {
            "inversion_layer_reduced":
                adjusted_stats["layer_rate_percent"]
                <= raw_stats["layer_rate_percent"],

            "inversion_column_reduced":
                adjusted_stats["column_rate_percent"]
                <= raw_stats["column_rate_percent"],

            "severity_reduced":
                adjusted_stats["aggregate_severity"]
                <= raw_stats["aggregate_severity"],
        },
    }