from __future__ import annotations

from datetime import date
from math import isfinite

import xarray as xr
from fastapi import APIRouter, Query

from ..coordinates import get_nearest_model_cell
from ..dataset import get_dashboard_dataset
from ..errors import DataNotAvailableError
from ..schemas import (
    CoordinateResponse,
    ProfileDepthPoint,
    ProfileResponse,
)


router = APIRouter()


@router.get("/profile", response_model=ProfileResponse)
def get_profile(
    date: date = Query(
        ...,
        description="Requested analysis date, YYYY-MM-DD",
    ),
    lat: float = Query(
        ...,
        ge=5.0,
        le=30.0,
        description="Latitude",
    ),
    lon: float = Query(
        ...,
        ge=45.0,
        le=105.0,
        description="Longitude",
    ),
) -> ProfileResponse:
    """
    Return the complete temperature/salinity depth profile for
    the nearest model ocean grid cell.

    The response contains:

    - requested date
    - actual data date used
    - model grid location
    - temperature at every model depth
    - temperature uncertainty
    - salinity at every model depth
    - salinity uncertainty
    - TCHP
    - D26
    - MLD
    - thermocline depth

    ARGO and ARMOR3D data are not used.
    """

    ds: xr.Dataset = get_dashboard_dataset()

    # ------------------------------------------------------------
    # 1. Validate required coordinates
    # ------------------------------------------------------------

    if "latitude" not in ds.coords:
        raise DataNotAvailableError(
            "Dashboard dataset has no latitude coordinate"
        )

    if "longitude" not in ds.coords:
        raise DataNotAvailableError(
            "Dashboard dataset has no longitude coordinate"
        )

    if "depth" not in ds.coords:
        raise DataNotAvailableError(
            "Dashboard dataset has no depth coordinate"
        )

    if "time" not in ds.coords:
        raise DataNotAvailableError(
            "Dashboard dataset has no time coordinate"
        )

    # ------------------------------------------------------------
    # 2. Resolve nearest model grid cell
    # ------------------------------------------------------------

    model_cell = get_nearest_model_cell(lat, lon)

    model_lat = float(model_cell.lat)
    model_lon = float(model_cell.lon)

    # ------------------------------------------------------------
    # 3. Verify model cell exists
    # ------------------------------------------------------------

    latitude_values = ds["latitude"].values
    longitude_values = ds["longitude"].values

    if not _coordinate_exists(latitude_values, model_lat):
        raise DataNotAvailableError(
            f"No latitude cell available for {model_lat}"
        )

    if not _coordinate_exists(longitude_values, model_lon):
        raise DataNotAvailableError(
            f"No longitude cell available for {model_lon}"
        )

    # ------------------------------------------------------------
    # 4. Resolve requested date
    #
    # We compare only calendar dates so the route does not depend
    # on whether xarray stores timestamps at midnight.
    # ------------------------------------------------------------

    target_time = _find_time_for_date(ds["time"], date)

    if target_time is None:
        times = ds["time"].values
        if len(times) > 0:
            target_time = times[0]
        else:
            raise DataNotAvailableError(
                f"No data available for {date.isoformat()}"
            )

    data_date = _timestamp_to_date(target_time).isoformat()

    # ------------------------------------------------------------
    # 5. Select requested time + nearest model cell
    # ------------------------------------------------------------

    point = ds.sel(
        time=target_time,
        latitude=model_lat,
        longitude=model_lon,
    )

    # ------------------------------------------------------------
    # 6. Build complete depth profile
    # ------------------------------------------------------------

    depths: list[ProfileDepthPoint] = []

    for depth in ds["depth"].values:

        depth_value = float(depth)

        temperature = _extract_depth_value(
            point,
            "temperature_mean",
            depth_value,
        )

        temperature_uncertainty = _extract_depth_value(
            point,
            "temperature_std",
            depth_value,
        )

        salinity = _extract_depth_value(
            point,
            "salinity_mean",
            depth_value,
        )

        salinity_uncertainty = _extract_depth_value(
            point,
            "salinity_std",
            depth_value,
        )

        depths.append(
            ProfileDepthPoint(
                depth=depth_value,
                temperature=temperature,
                temperature_uncertainty=temperature_uncertainty,
                salinity=salinity,
                salinity_uncertainty=salinity_uncertainty,
            )
        )

    # ------------------------------------------------------------
    # 7. Extract scalar business variables
    # ------------------------------------------------------------

    tchp = _extract_scalar(point, "tchp")
    d26 = _extract_scalar(point, "d26")
    mld = _extract_scalar(point, "mld")
    thermocline_depth = _extract_scalar(
        point,
        "thermocline_depth",
    )

    # ------------------------------------------------------------
    # 8. Return response
    # ------------------------------------------------------------

    return ProfileResponse(
        location=CoordinateResponse(
            lat=model_lat,
            lon=model_lon,
        ),
        requestedDate=date.isoformat(),
        dataDate=data_date,
        depths=depths,
        tchp=tchp,
        d26=d26,
        mld=mld,
        thermoclineDepth=thermocline_depth,
    )


# ==================================================================
# Helpers
# ==================================================================


def _find_time_for_date(
    time_coord: xr.DataArray,
    requested_date: date,
):
    """
    Find the dataset timestamp corresponding to a calendar date.

    Returns the original xarray/numpy timestamp or None.
    """

    for timestamp in time_coord.values:

        if _timestamp_to_date(timestamp) == requested_date:
            return timestamp

    return None


def _timestamp_to_date(timestamp) -> date:
    """
    Convert numpy/xarray datetime values into Python date.
    """

    timestamp_str = str(
        xr.DataArray(timestamp).values.astype("datetime64[D]")
    )

    return date.fromisoformat(timestamp_str)


def _coordinate_exists(
    values,
    requested: float,
    tolerance: float = 1e-6,
) -> bool:
    """
    Check whether a model coordinate exists within tolerance.
    """

    for value in values:
        if abs(float(value) - requested) <= tolerance:
            return True

    return False


def _extract_depth_value(
    point: xr.Dataset,
    variable: str,
    depth: float,
) -> float | None:
    """
    Extract a depth-specific variable.

    Missing variables or invalid values are returned as None.
    """

    if variable not in point.data_vars:
        return None

    try:
        value = point[variable].sel(
            depth=depth,
            method="nearest",
        ).values
    except Exception:
        return None

    return _to_float_or_none(value)


def _extract_scalar(
    point: xr.Dataset,
    variable: str,
) -> float | None:
    """
    Extract a scalar dataset variable.

    Missing variables and NaN/inf values become None.
    """

    if variable not in point.data_vars:
        return None

    try:
        value = point[variable].values
    except Exception:
        return None

    return _to_float_or_none(value)


def _to_float_or_none(value) -> float | None:
    """
    Convert a dataset value into a JSON-safe float.

    NaN and infinity are treated as unavailable data.
    """

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    return value if isfinite(value) else None