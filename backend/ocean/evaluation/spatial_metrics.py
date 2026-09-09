from __future__ import annotations

import numpy as np


def initialize_spatial_accumulators(
    n_lat: int,
    n_lon: int,
) -> dict[str, np.ndarray]:
    """
    Initialize memory-safe accumulators for spatial error metrics.

    Accumulation is performed over time and depth.
    """
    return {
        "temperature_sse": np.zeros((n_lat, n_lon), dtype=np.float64),
        "temperature_sae": np.zeros((n_lat, n_lon), dtype=np.float64),
        "temperature_count": np.zeros((n_lat, n_lon), dtype=np.int64),

        "salinity_sse": np.zeros((n_lat, n_lon), dtype=np.float64),
        "salinity_sae": np.zeros((n_lat, n_lon), dtype=np.float64),
        "salinity_count": np.zeros((n_lat, n_lon), dtype=np.int64),
    }


def update_spatial_accumulators(
    accumulators: dict[str, np.ndarray],
    temperature_prediction: np.ndarray,
    temperature_truth: np.ndarray,
    salinity_prediction: np.ndarray,
    salinity_truth: np.ndarray,
) -> None:
    """
    Update spatial error accumulators using one time chunk.

    Expected shape:
        (time, depth, latitude, longitude)
    """

    _update_variable(
        prediction=temperature_prediction,
        truth=temperature_truth,
        sse=accumulators["temperature_sse"],
        sae=accumulators["temperature_sae"],
        count=accumulators["temperature_count"],
    )

    _update_variable(
        prediction=salinity_prediction,
        truth=salinity_truth,
        sse=accumulators["salinity_sse"],
        sae=accumulators["salinity_sae"],
        count=accumulators["salinity_count"],
    )


def _update_variable(
    prediction: np.ndarray,
    truth: np.ndarray,
    sse: np.ndarray,
    sae: np.ndarray,
    count: np.ndarray,
) -> None:
    """
    Accumulate errors over time and depth for every spatial cell.
    """

    valid = np.isfinite(prediction) & np.isfinite(truth)

    error = prediction - truth

    # Invalid values must not enter the reductions.
    squared_error = np.where(valid, error * error, 0.0)
    absolute_error = np.where(valid, np.abs(error), 0.0)

    # Reduce time + depth, preserving latitude + longitude.
    sse += np.sum(squared_error, axis=(0, 1), dtype=np.float64)
    sae += np.sum(absolute_error, axis=(0, 1), dtype=np.float64)
    count += np.sum(valid, axis=(0, 1), dtype=np.int64)


def finalize_spatial_metrics(
    accumulators: dict[str, np.ndarray],
) -> dict:
    """
    Convert accumulated errors into spatial RMSE/MAE grids.
    """

    def finalize(
        sse: np.ndarray,
        sae: np.ndarray,
        count: np.ndarray,
    ) -> dict:
        rmse = np.full_like(sse, np.nan, dtype=np.float64)
        mae = np.full_like(sae, np.nan, dtype=np.float64)

        valid = count > 0

        rmse[valid] = np.sqrt(sse[valid] / count[valid])
        mae[valid] = sae[valid] / count[valid]

        return {
            "rmse": rmse,
            "mae": mae,
            "valid_count": count.copy(),
        }

    temperature = finalize(
        accumulators["temperature_sse"],
        accumulators["temperature_sae"],
        accumulators["temperature_count"],
    )

    salinity = finalize(
        accumulators["salinity_sse"],
        accumulators["salinity_sae"],
        accumulators["salinity_count"],
    )

    return {
        "temperature": temperature,
        "salinity": salinity,
    }