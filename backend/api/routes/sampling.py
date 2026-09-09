from __future__ import annotations

from datetime import date
from math import isfinite

import numpy as np
from fastapi import APIRouter, Query

from ..coordinates import get_nearest_model_cell
from ..dataset import get_dashboard_dataset
from ..errors import DataNotAvailableError
from ..schemas import SamplingRecommendation


router = APIRouter(
    prefix="/sampling",
    tags=["sampling"],
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TEMPERATURE_WEIGHT = 0.5
SALINITY_WEIGHT = 0.5

LOW_THRESHOLD = 0.33
MEDIUM_THRESHOLD = 0.66

DEFAULT_TOP_N = 20
MAX_TOP_N = 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(value) -> float | None:
    """
    Convert a scalar value to a JSON-safe float.

    NaN / inf are treated as unavailable.
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    return value if isfinite(value) else None


def _validate_date(ds, requested_date: date) -> str:
    """
    Validate that the requested date exists in the dashboard dataset.
    """

    if "time" not in ds.coords:
        raise DataNotAvailableError(
            "Dashboard dataset has no time coordinate"
        )

    available_dates = ds["time"].dt.date.values

    if requested_date not in available_dates:
        raise DataNotAvailableError(
            f"No sampling data available for "
            f"{requested_date.isoformat()}"
        )

    return requested_date.isoformat()


def _validate_required_variables(ds) -> None:
    """
    Ensure the dashboard dataset contains the uncertainty fields required
    for adaptive sampling.
    """

    required = (
        "temperature_std",
        "salinity_std",
    )

    missing = [
        name
        for name in required
        if name not in ds.data_vars
    ]

    if missing:
        raise DataNotAvailableError(
            f"Required sampling variables are missing: {missing}"
        )


def _normalize_uncertainty(
    temperature_std: np.ndarray,
    salinity_std: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Normalize temperature and salinity uncertainty independently.

    Normalization is performed over the requested analysis date so that
    the sampling score represents relative uncertainty within that field.
    """

    def normalize(values: np.ndarray) -> np.ndarray:
        finite = np.isfinite(values)

        if not np.any(finite):
            return np.full_like(values, np.nan, dtype=np.float32)

        valid = values[finite]

        low = float(np.nanmin(valid))
        high = float(np.nanmax(valid))

        if high <= low:
            result = np.zeros_like(values, dtype=np.float32)
            result[~finite] = np.nan
            return result

        result = (values - low) / (high - low)
        result[~finite] = np.nan

        return result.astype(np.float32)

    return normalize(temperature_std), normalize(salinity_std)


def _priority_from_score(score: float) -> str:
    if score >= MEDIUM_THRESHOLD:
        return "high"

    if score >= LOW_THRESHOLD:
        return "medium"

    return "low"


def _build_reasons(
    temperature_uncertainty: float | None,
    salinity_uncertainty: float | None,
    score: float,
) -> list[str]:

    reasons: list[str] = []

    if temperature_uncertainty is not None:
        reasons.append(
            f"temperature uncertainty={temperature_uncertainty:.4f}"
        )

    if salinity_uncertainty is not None:
        reasons.append(
            f"salinity uncertainty={salinity_uncertainty:.4f}"
        )

    if score >= MEDIUM_THRESHOLD:
        reasons.append("high combined uncertainty")

    elif score >= LOW_THRESHOLD:
        reasons.append("moderate combined uncertainty")

    else:
        reasons.append("low combined uncertainty")

    return reasons


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=list[SamplingRecommendation],
)
def get_sampling_recommendations(
    date: date = Query(
        ...,
        description="Analysis date, YYYY-MM-DD",
    ),
    lat: float | None = Query(
        None,
        ge=-90.0,
        le=90.0,
        description="Optional latitude of the requested model region",
    ),
    lon: float | None = Query(
        None,
        ge=-180.0,
        le=180.0,
        description="Optional longitude of the requested model region",
    ),
    top_n: int = Query(
        DEFAULT_TOP_N,
        ge=1,
        le=MAX_TOP_N,
        description="Number of sampling recommendations to return",
    ),
) -> list[SamplingRecommendation]:

    ds = get_dashboard_dataset()

    # ---------------------------------------------------------------
    # 1. Validate required dataset contents
    # ---------------------------------------------------------------

    _validate_required_variables(ds)

    requested_date = _validate_date(ds, date)

    # ---------------------------------------------------------------
    # 2. Select requested analysis date
    # ---------------------------------------------------------------

    day = ds.sel(
        time=requested_date,
        method="nearest",
    )

    if "depth" not in day.coords:
        raise DataNotAvailableError(
            "Dashboard dataset has no depth coordinate"
        )

    surface_depth = float(day["depth"].values[0])

    temperature_surface = np.asarray(
        day["temperature_std"]
        .sel(depth=surface_depth)
        .values,
        dtype=np.float32,
    )

    salinity_surface = np.asarray(
        day["salinity_std"]
        .sel(depth=surface_depth)
        .values,
        dtype=np.float32,
    )

    temperature_norm, salinity_norm = _normalize_uncertainty(
        temperature_surface,
        salinity_surface,
    )

    score = (
        TEMPERATURE_WEIGHT * temperature_norm
        + SALINITY_WEIGHT * salinity_norm
    )
    # ---------------------------------------------------------------
    # 5. Restrict to surface/model-grid coordinates
    #
    # Sampling recommendations are horizontal locations, therefore use
    # the surface depth level rather than generating one recommendation
    # for every depth.
    # ---------------------------------------------------------------

    if "depth" in day.coords:
        surface_depth = float(day["depth"].values[0])

        temperature_surface = np.asarray(
            day["temperature_std"]
            .sel(depth=surface_depth)
            .values,
            dtype=np.float32,
        )

        salinity_surface = np.asarray(
            day["salinity_std"]
            .sel(depth=surface_depth)
            .values,
            dtype=np.float32,
        )

        temperature_norm, salinity_norm = _normalize_uncertainty(
            temperature_surface,
            salinity_surface,
        )

        score = (
            TEMPERATURE_WEIGHT * temperature_norm
            + SALINITY_WEIGHT * salinity_norm
        )

    # ---------------------------------------------------------------
    # 6. Coordinates
    # ---------------------------------------------------------------

    if "latitude" not in day.coords or "longitude" not in day.coords:
        raise DataNotAvailableError(
            "Dashboard dataset has no latitude/longitude coordinates"
        )

    latitudes = np.asarray(day["latitude"].values)
    longitudes = np.asarray(day["longitude"].values)

    # ---------------------------------------------------------------
    # 7. Optional location restriction
    #
    # If a user clicked a model cell, return recommendations around
    # that cell. Otherwise return the globally highest-priority cells.
    # ---------------------------------------------------------------

    candidate_indices = np.argwhere(np.isfinite(score))

    if lat is not None and lon is not None:

        cell = get_nearest_model_cell(lat, lon)

        # Find nearest latitude/longitude indices.
        lat_idx = int(
            np.abs(latitudes - cell.lat).argmin()
        )

        lon_idx = int(
            np.abs(longitudes - cell.lon).argmin()
        )

        # Restrict recommendations to a local 5x5 grid neighborhood.
        lat_min = max(0, lat_idx - 2)
        lat_max = min(len(latitudes), lat_idx + 3)

        lon_min = max(0, lon_idx - 2)
        lon_max = min(len(longitudes), lon_idx + 3)

        local_candidates = []

        for i in range(lat_min, lat_max):
            for j in range(lon_min, lon_max):
                if np.isfinite(score[i, j]):
                    local_candidates.append((i, j))

        candidate_indices = np.asarray(
            local_candidates,
            dtype=int,
        )

        if candidate_indices.size == 0:
            return []

    # ---------------------------------------------------------------
    # 8. Sort by descending sampling score
    # ---------------------------------------------------------------

    ranked = sorted(
        candidate_indices.tolist(),
        key=lambda idx: float(score[idx[0], idx[1]]),
        reverse=True,
    )

    ranked = ranked[:top_n]

    # ---------------------------------------------------------------
    # 9. Build recommendations
    # ---------------------------------------------------------------

    recommendations: list[SamplingRecommendation] = []

    for i, j in ranked:

        sampling_score = _safe_float(score[i, j])

        if sampling_score is None:
            continue

        temp_uncertainty = _safe_float(
            temperature_norm[i, j]
        )

        salt_uncertainty = _safe_float(
            salinity_norm[i, j]
        )

        recommendations.append(
            SamplingRecommendation(
                lat=float(latitudes[i]),
                lon=float(longitudes[j]),
                priority=_priority_from_score(sampling_score),
                score=sampling_score,
                reasons=_build_reasons(
                    temp_uncertainty,
                    salt_uncertainty,
                    sampling_score,
                ),
            )
        )

    return recommendations