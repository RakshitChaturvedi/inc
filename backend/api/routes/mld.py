from __future__ import annotations

from datetime import date
from math import isfinite

from fastapi import APIRouter, Query

from ..coordinates import get_nearest_model_cell
from ..dataset import get_dashboard_dataset
from ..errors import DataNotAvailableError
from ..schemas import CoordinateResponse, MldResponse


router = APIRouter(
    prefix="/mld",
    tags=["mld"],
)


def _safe_float(value) -> float | None:
    """Convert a scalar dataset value to a JSON-safe float."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    return value if isfinite(value) else None


@router.get("", response_model=MldResponse)
def get_mld(
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
) -> MldResponse:

    ds = get_dashboard_dataset()

    # ---------------------------------------------------------------
    # 1. Validate required variable
    # ---------------------------------------------------------------

    if "mld" not in ds.data_vars:
        raise DataNotAvailableError(
            "Required dashboard variable 'mld' is missing"
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
            f"No MLD data available for {date.isoformat()}"
        )

    # ---------------------------------------------------------------
    # 3. Resolve click to nearest model grid cell
    # ---------------------------------------------------------------

    cell = get_nearest_model_cell(lat, lon)

    # ---------------------------------------------------------------
    # 4. Select exact model cell
    # ---------------------------------------------------------------

    point = ds.sel(
        time=date.isoformat(),
        latitude=cell.lat,
        longitude=cell.lon,
    )

    # ---------------------------------------------------------------
    # 5. Extract MLD
    # ---------------------------------------------------------------

    mld = _safe_float(point["mld"].values)

    # ---------------------------------------------------------------
    # 6. Return
    # ---------------------------------------------------------------

    return MldResponse(
        location=CoordinateResponse(
            lat=float(cell.lat),
            lon=float(cell.lon),
        ),
        date=date.isoformat(),
        value=mld,
    )