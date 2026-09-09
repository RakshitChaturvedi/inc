from __future__ import annotations

from datetime import date
from math import isfinite

from fastapi import APIRouter, Query

from ..coordinates import get_nearest_model_cell
from ..dataset import get_dashboard_dataset
from ..errors import DataNotAvailableError
from ..schemas import CoordinateResponse, TchpResponse


router = APIRouter(
    prefix="/tchp",
    tags=["tchp"],
)


def _safe_float(value) -> float | None:
    """Convert a scalar dataset value to a JSON-safe float."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    return value if isfinite(value) else None


def _get_category(value: float | None) -> str | None:
    """
    Classify TCHP using the project's existing business thresholds.
    """
    if value is None:
        return None

    if value < 40:
        return "Too Low"

    if value < 60:
        return "Medium (Baseline)"

    if value < 90:
        return "High (Good)"

    return "Too High (Extreme Energy)"


@router.get("", response_model=TchpResponse)
def get_tchp(
    date: date = Query(
        ...,
        description="Analysis date, YYYY-MM-DD",
    ),
    lat: float = Query(
        ...,
        ge=-90.0,
        le=90.0,
    ),
    lon: float = Query(
        ...,
        ge=-180.0,
        le=180.0,
    ),
) -> TchpResponse:

    ds = get_dashboard_dataset()

    # ---------------------------------------------------------------
    # 1. Validate required variables
    # ---------------------------------------------------------------

    required = ("tchp", "d26")

    missing = [
        name
        for name in required
        if name not in ds.data_vars
    ]

    if missing:
        raise DataNotAvailableError(
            f"Required dashboard variables are missing: {missing}"
        )

    # ---------------------------------------------------------------
    # 2. Validate time coordinate
    # ---------------------------------------------------------------

    if "time" not in ds.coords:
        raise DataNotAvailableError(
            "Dashboard dataset has no time coordinate"
        )

    available_dates = ds["time"].dt.date.values

    if date not in available_dates:
        raise DataNotAvailableError(
            f"No TCHP data available for {date.isoformat()}"
        )

    # ---------------------------------------------------------------
    # 3. Resolve click to nearest model grid cell
    # ---------------------------------------------------------------

    cell = get_nearest_model_cell(lat, lon)

    # ---------------------------------------------------------------
    # 4. Select the model point
    # ---------------------------------------------------------------

    point = ds.sel(
        time=date.isoformat(),
        latitude=cell.lat,
        longitude=cell.lon,
    )

    # ---------------------------------------------------------------
    # 5. Extract business variables
    # ---------------------------------------------------------------

    tchp = _safe_float(
        point["tchp"].values
    )

    d26 = _safe_float(
        point["d26"].values
    )

    # ---------------------------------------------------------------
    # 6. Return
    # ---------------------------------------------------------------

    return TchpResponse(
        location=CoordinateResponse(
            lat=float(cell.lat),
            lon=float(cell.lon),
        ),
        date=date.isoformat(),
        value=tchp,
        category=_get_category(tchp),
        d26=d26,
    )