from __future__ import annotations

from datetime import date
from math import isfinite

from fastapi import APIRouter, Query

from ..coordinates import get_nearest_model_cell
from ..dataset import get_dashboard_dataset
from ..errors import DataNotAvailableError
from ..schemas import CoordinateResponse, D26Response


router = APIRouter(
    prefix="/d26",
    tags=["d26"],
)


def _safe_float(value) -> float | None:
    """Convert a scalar dataset value to a JSON-safe float."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    return value if isfinite(value) else None


@router.get("", response_model=D26Response)
def get_d26(
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
) -> D26Response:

    ds = get_dashboard_dataset()

    # ---------------------------------------------------------------
    # 1. Validate required variables
    # ---------------------------------------------------------------

    required = ("d26", "tchp")

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
            f"No D26 data available for {date.isoformat()}"
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

    d26 = _safe_float(
        point["d26"].values
    )

    tchp = _safe_float(
        point["tchp"].values
    )

    # ---------------------------------------------------------------
    # 6. Return
    # ---------------------------------------------------------------

    return D26Response(
        location=CoordinateResponse(
            lat=float(cell.lat),
            lon=float(cell.lon),
        ),
        date=date.isoformat(),
        value=d26,
        tchp=tchp,
    )