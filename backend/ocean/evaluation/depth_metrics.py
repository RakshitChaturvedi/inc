from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_DEPTHS = [0.0, 5.0, 100.0, 1000.0]

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PREDICTION_PATH = (
    PROJECT_ROOT
    / "data"
    / "physics"
    / "physics_adjusted.nc"
)

TEMPERATURE_TARGET_PATH = (
    PROJECT_ROOT
    / "data"
    / "evaluation"
    / "temperature_targets_masked.nc"
)

SALINITY_TARGET_PATH = (
    PROJECT_ROOT
    / "data"
    / "evaluation"
    / "salinity_targets_masked.nc"
)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_dataset_alignment(
    prediction_ds: xr.Dataset,
    target_ds: xr.Dataset,
    target_variable: str,
) -> None:
    """
    Validate that prediction and target datasets describe the same grid.
    """

    required_prediction = (
        "temperature_mean"
        if target_variable == "temperature"
        else "salinity_mean"
    )

    if required_prediction not in prediction_ds:
        raise ValueError(
            f"Prediction dataset missing '{required_prediction}'"
        )

    if target_variable not in target_ds:
        raise ValueError(
            f"Target dataset missing '{target_variable}'"
        )

    pred = prediction_ds[required_prediction]
    truth = target_ds[target_variable]

    required_dims = {"time", "depth", "latitude", "longitude"}

    if not required_dims.issubset(pred.dims):
        raise ValueError(
            f"Prediction dimensions are {pred.dims}; "
            f"expected dimensions containing {required_dims}"
        )

    if not required_dims.issubset(truth.dims):
        raise ValueError(
            f"Target dimensions are {truth.dims}; "
            f"expected dimensions containing {required_dims}"
        )

    for coord in ("time", "depth", "latitude", "longitude"):
        if not np.array_equal(
            prediction_ds[coord].values,
            target_ds[coord].values,
        ):
            raise ValueError(
                f"Coordinate mismatch detected for '{coord}'"
            )


# ---------------------------------------------------------------------------
# Metric calculation
# ---------------------------------------------------------------------------

def _calculate_metrics(
    prediction: xr.DataArray,
    truth: xr.DataArray,
) -> dict[str, Any]:
    """
    Calculate scalar regression metrics over all valid grid cells.

    NaN values in either prediction or target are ignored.
    """

    pred = np.asarray(prediction.values, dtype=np.float64)
    actual = np.asarray(truth.values, dtype=np.float64)

    valid = np.isfinite(pred) & np.isfinite(actual)

    pred_valid = pred[valid]
    actual_valid = actual[valid]

    n_valid = int(valid.sum())

    if n_valid == 0:
        return {
            "n_valid": 0,
            "rmse": None,
            "mae": None,
            "bias": None,
            "r2": None,
        }

    error = pred_valid - actual_valid

    mse = np.mean(error ** 2)
    rmse = float(np.sqrt(mse))
    mae = float(np.mean(np.abs(error)))
    bias = float(np.mean(error))

    ss_res = float(np.sum(error ** 2))
    centered_truth = actual_valid - np.mean(actual_valid)
    ss_tot = float(np.sum(centered_truth ** 2))

    if ss_tot > 0:
        r2 = float(1.0 - ss_res / ss_tot)
    else:
        r2 = None

    return {
        "n_valid": n_valid,
        "rmse": rmse,
        "mae": mae,
        "bias": bias,
        "r2": r2,
    }


# ---------------------------------------------------------------------------
# Depth resolution
# ---------------------------------------------------------------------------

def _resolve_depth(
    available_depths: np.ndarray,
    requested_depth: float,
) -> float:
    """
    Resolve a requested depth against the dataset depth coordinate.

    Exact matching is preferred. If no exact match exists, the nearest
    available depth is selected.
    """

    available = np.asarray(available_depths, dtype=np.float64)

    exact = np.where(np.isclose(available, requested_depth))[0]

    if len(exact) > 0:
        return float(available[exact[0]])

    nearest_idx = int(
        np.argmin(np.abs(available - requested_depth))
    )

    return float(available[nearest_idx])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_depth_metrics(
    prediction_ds: xr.Dataset,
    target_ds: xr.Dataset,
    variable: str,
    depths: list[float] | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Calculate prediction metrics at selected depth levels.

    Parameters
    ----------
    prediction_ds:
        Dataset containing physics-adjusted predictions.

    target_ds:
        Dataset containing masked ground truth.

    variable:
        Either "temperature" or "salinity".

    depths:
        Requested depth levels in metres.

    Returns
    -------
    dict
        Metrics keyed by depth.

    Example
    -------
    {
        "0m": {
            "requested_depth_m": 0.0,
            "actual_depth_m": 0.0,
            "n_valid": 123456,
            "rmse": ...,
            "mae": ...,
            "bias": ...,
            "r2": ...
        }
    }
    """

    if variable not in {"temperature", "salinity"}:
        raise ValueError(
            f"Unsupported variable '{variable}'. "
            "Expected 'temperature' or 'salinity'."
        )

    if depths is None:
        depths = DEFAULT_DEPTHS

    _validate_dataset_alignment(
        prediction_ds,
        target_ds,
        variable,
    )

    prediction_variable = (
        "temperature_mean"
        if variable == "temperature"
        else "salinity_mean"
    )

    prediction = prediction_ds[prediction_variable]
    truth = target_ds[variable]

    available_depths = prediction.depth.values

    results: dict[str, dict[str, Any]] = {}

    for requested_depth in depths:

        actual_depth = _resolve_depth(
            available_depths,
            requested_depth,
        )

        pred_slice = prediction.sel(
            depth=actual_depth
        )

        truth_slice = truth.sel(
            depth=actual_depth
        )

        metrics = _calculate_metrics(
            pred_slice,
            truth_slice,
        )

        key = f"{int(requested_depth)}m"

        results[key] = {
            "requested_depth_m": float(requested_depth),
            "actual_depth_m": float(actual_depth),
            **metrics,
        }

    return results


def calculate_all_depth_metrics(
    prediction_ds: xr.Dataset,
    temperature_target_ds: xr.Dataset,
    salinity_target_ds: xr.Dataset,
    depths: list[float] | None = None,
) -> dict[str, dict[str, dict[str, Any]]]:
    """
    Calculate depth metrics for both temperature and salinity.
    """

    if depths is None:
        depths = DEFAULT_DEPTHS

    return {
        "temperature": calculate_depth_metrics(
            prediction_ds=prediction_ds,
            target_ds=temperature_target_ds,
            variable="temperature",
            depths=depths,
        ),
        "salinity": calculate_depth_metrics(
            prediction_ds=prediction_ds,
            target_ds=salinity_target_ds,
            variable="salinity",
            depths=depths,
        ),
    }


# ---------------------------------------------------------------------------
# Standalone execution
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 80)
    print("OceanEmbed — Depth Evaluation")
    print("=" * 80)

    print(f"\nPrediction : {PREDICTION_PATH}")
    print(f"Temperature: {TEMPERATURE_TARGET_PATH}")
    print(f"Salinity   : {SALINITY_TARGET_PATH}")

    for path in (
        PREDICTION_PATH,
        TEMPERATURE_TARGET_PATH,
        SALINITY_TARGET_PATH,
    ):
        if not path.exists():
            raise FileNotFoundError(
                f"Required file does not exist: {path}"
            )

    print("\nOpening datasets...")

    with (
        xr.open_dataset(PREDICTION_PATH) as prediction_ds,
        xr.open_dataset(TEMPERATURE_TARGET_PATH) as temperature_ds,
        xr.open_dataset(SALINITY_TARGET_PATH) as salinity_ds,
    ):
        print("PASS: datasets opened")

        results = calculate_all_depth_metrics(
            prediction_ds,
            temperature_ds,
            salinity_ds,
            depths=DEFAULT_DEPTHS,
        )

    print("\n" + "=" * 80)
    print("DEPTH METRICS")
    print("=" * 80)

    for variable, depth_results in results.items():

        print(f"\n{variable.upper()}")
        print("-" * 80)

        print(
            f"{'Depth':>8} | "
            f"{'RMSE':>12} | "
            f"{'MAE':>12} | "
            f"{'Bias':>12} | "
            f"{'R²':>12} | "
            f"{'Valid':>12}"
        )

        print("-" * 80)

        for depth, metrics in depth_results.items():

            rmse = metrics["rmse"]
            mae = metrics["mae"]
            bias = metrics["bias"]
            r2 = metrics["r2"]

            print(
                f"{depth:>8} | "
                f"{rmse if rmse is not None else 'N/A':>12} | "
                f"{mae if mae is not None else 'N/A':>12} | "
                f"{bias if bias is not None else 'N/A':>12} | "
                f"{r2 if r2 is not None else 'N/A':>12} | "
                f"{metrics['n_valid']:>12}"
            )

    print("\n" + "=" * 80)
    print("DEPTH EVALUATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()