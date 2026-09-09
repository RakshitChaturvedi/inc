from __future__ import annotations

import numpy as np


DEFAULT_N_BINS = 20


def initialize_uncertainty_accumulators(
    n_bins: int = DEFAULT_N_BINS,
) -> dict[str, np.ndarray]:
    """
    Initialize accumulators for uncertainty-error calibration.

    Statistics are accumulated independently for temperature
    and salinity.
    """

    return {
        "temperature_count": np.zeros(n_bins, dtype=np.int64),
        "temperature_sse": np.zeros(n_bins, dtype=np.float64),
        "temperature_sae": np.zeros(n_bins, dtype=np.float64),
        "temperature_uncertainty_sum": np.zeros(n_bins, dtype=np.float64),

        "salinity_count": np.zeros(n_bins, dtype=np.int64),
        "salinity_sse": np.zeros(n_bins, dtype=np.float64),
        "salinity_sae": np.zeros(n_bins, dtype=np.float64),
        "salinity_uncertainty_sum": np.zeros(n_bins, dtype=np.float64),
    }


def update_uncertainty_accumulators(
    accumulators: dict[str, np.ndarray],
    prediction: np.ndarray,
    truth: np.ndarray,
    uncertainty: np.ndarray,
    variable: str,
    bin_edges: np.ndarray,
) -> None:
    """
    Update uncertainty/error statistics for one time chunk.

    Expected shapes:
        (time, depth, latitude, longitude)
    """

    valid = (
        np.isfinite(prediction)
        & np.isfinite(truth)
        & np.isfinite(uncertainty)
        & (uncertainty >= 0)
    )

    if not np.any(valid):
        return

    pred = prediction[valid]
    true = truth[valid]
    std = uncertainty[valid]

    error = pred - true

    # Find uncertainty bins.
    bin_indices = np.searchsorted(
        bin_edges,
        std,
        side="right",
    ) - 1

    n_bins = len(bin_edges) - 1

    valid_bins = (
        (bin_indices >= 0)
        & (bin_indices < n_bins)
    )

    bin_indices = bin_indices[valid_bins]
    error = error[valid_bins]
    std = std[valid_bins]

    count_key = f"{variable}_count"
    sse_key = f"{variable}_sse"
    sae_key = f"{variable}_sae"
    uncertainty_key = f"{variable}_uncertainty_sum"

    accumulators[count_key] += np.bincount(
        bin_indices,
        minlength=n_bins,
    )

    accumulators[sse_key] += np.bincount(
        bin_indices,
        weights=error ** 2,
        minlength=n_bins,
    )

    accumulators[sae_key] += np.bincount(
        bin_indices,
        weights=np.abs(error),
        minlength=n_bins,
    )

    accumulators[uncertainty_key] += np.bincount(
        bin_indices,
        weights=std,
        minlength=n_bins,
    )


def finalize_uncertainty_metrics(
    accumulators: dict[str, np.ndarray],
    bin_edges: np.ndarray,
) -> dict:
    """
    Produce uncertainty calibration statistics.
    """

    n_bins = len(bin_edges) - 1

    def finalize(variable: str) -> dict:
        count = accumulators[f"{variable}_count"]
        sse = accumulators[f"{variable}_sse"]
        sae = accumulators[f"{variable}_sae"]
        uncertainty_sum = accumulators[
            f"{variable}_uncertainty_sum"
        ]

        rmse = np.full(n_bins, np.nan, dtype=np.float64)
        mae = np.full(n_bins, np.nan, dtype=np.float64)
        mean_uncertainty = np.full(
            n_bins,
            np.nan,
            dtype=np.float64,
        )

        valid = count > 0

        rmse[valid] = np.sqrt(
            sse[valid] / count[valid]
        )

        mae[valid] = (
            sae[valid] / count[valid]
        )

        mean_uncertainty[valid] = (
            uncertainty_sum[valid] / count[valid]
        )

        return {
            "count": count.tolist(),
            "mean_uncertainty": mean_uncertainty.tolist(),
            "rmse": rmse.tolist(),
            "mae": mae.tolist(),
        }

    return {
        "bin_edges": bin_edges.tolist(),
        "temperature": finalize("temperature"),
        "salinity": finalize("salinity"),
    }


def calculate_uncertainty_error_correlation(
    uncertainty: np.ndarray,
    truth: np.ndarray,
    prediction: np.ndarray,
) -> float | None:
    """
    Calculate Pearson correlation between ensemble uncertainty
    and absolute prediction error.

    Intended for one chunk or a separately accumulated sample.
    """

    valid = (
        np.isfinite(uncertainty)
        & np.isfinite(truth)
        & np.isfinite(prediction)
    )

    if valid.sum() < 2:
        return None

    u = uncertainty[valid].astype(np.float64)
    error = np.abs(
        prediction[valid] - truth[valid]
    ).astype(np.float64)

    if np.std(u) == 0.0 or np.std(error) == 0.0:
        return None

    return float(np.corrcoef(u, error)[0, 1])