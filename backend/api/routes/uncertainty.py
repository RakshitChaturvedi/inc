# backend/api/routes/uncertainty.py

from __future__ import annotations

from datetime import date
from math import isfinite

from fastapi import APIRouter, Query

from ..coordinates import get_nearest_model_cell
from ..dataset import get_dashboard_dataset
from ..errors import DataNotAvailableError
from ..schemas import CoordinateResponse, UncertaintyResponse


router = APIRouter(
    prefix="/uncertainty",
    tags=["uncertainty"],
)


def _safe_float(value) -> float | None:
    """
    Convert a scalar dataset value to a JSON-safe float.

    NaN / inf values are treated as unavailable data.
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    return value if isfinite(value) else None


def _validate_depth(ds, depth: float) -> float:
    """
    Resolve the requested depth to an exact model depth.

    The frontend uses the model depth levels directly, but this also
    protects the API from arbitrary depth requests.
    """
    if "depth" not in ds.coords:
        raise DataNotAvailableError("Dashboard dataset has no depth coordinate")

    depths = ds["depth"].values

    if len(depths) == 0:
        raise DataNotAvailableError("No model depth levels are available")

    for model_depth in depths:
        if abs(float(model_depth) - depth) < 1e-6:
            return float(model_depth)

    raise DataNotAvailableError(
        f"Depth {depth} is not available. "
        f"Available depths: {[float(d) for d in depths]}"
    )


@router.get("", response_model=UncertaintyResponse)
def get_uncertainty(
    date: date = Query(..., description="Analysis date, YYYY-MM-DD"),
    lat: float = Query(..., ge=-90.0, le=90.0),
    lon: float = Query(..., ge=-180.0, le=180.0),
    depth: float = Query(..., ge=0.0),
) -> UncertaintyResponse:

    ds = get_dashboard_dataset()

    # ---------------------------------------------------------------
    # 1. Resolve geographic coordinate to nearest model grid cell
    # ---------------------------------------------------------------
    cell = get_nearest_model_cell(lat, lon)

    # ---------------------------------------------------------------
    # 2. Resolve requested depth against model depth coordinate
    # ---------------------------------------------------------------
    model_depth = _validate_depth(ds, depth)

    # ---------------------------------------------------------------
    # 3. Validate requested date
    # ---------------------------------------------------------------
    if "time" not in ds.coords:
        raise DataNotAvailableError("Dashboard dataset has no time coordinate")

    times = ds["time"]

    requested_date = date

    # Compare using the date portion so the API is not sensitive to
    # whether xarray stores timestamps at midnight or as datetime64.
    available_dates = times.dt.date.values

    if requested_date not in available_dates:
        raise DataNotAvailableError(
            f"No uncertainty data available for {requested_date.isoformat()}"
        )

    # ---------------------------------------------------------------
    # 4. Check required uncertainty variables
    # ---------------------------------------------------------------
    required = ("temperature_std", "salinity_std")

    missing = [name for name in required if name not in ds.data_vars]

    if missing:
        raise DataNotAvailableError(
            f"Required uncertainty variables are missing: {missing}"
        )

    # ---------------------------------------------------------------
    # 5. Select the exact model point
    # ---------------------------------------------------------------
    point = ds.sel(
        time=requested_date.isoformat(),
        depth=model_depth,
        latitude=cell.lat,
        longitude=cell.lon,
    )

    temperature_uncertainty = _safe_float(
        point["temperature_std"].values
    )

    salinity_uncertainty = _safe_float(
        point["salinity_std"].values
    )

    # ---------------------------------------------------------------
    # 6. Return API response
    # ---------------------------------------------------------------
    return UncertaintyResponse(
        location=CoordinateResponse(
            lat=float(cell.lat),
            lon=float(cell.lon),
        ),
        date=requested_date.isoformat(),
        depth=model_depth,
        temperature=temperature_uncertainty,
        salinity=salinity_uncertainty,
    )