from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dataset import OceanDataset
from ..dependencies import get_dataset
from ..schemas import FieldPoint, FieldResponse


router = APIRouter(
    prefix="/field",
    tags=["field"],
)


FIELD_VARIABLES = {
    "temperature": "temperature_mean",
    "salinity": "salinity_mean",
    "tchp": "tchp",
    "d26": "d26",
    "mld": "mld",
}


@router.get("", response_model=FieldResponse)
def get_field(
    variable: str = Query(...),
    date: date = Query(...),
    depth: float | None = Query(None),
    stride: int = Query(1, ge=1),
    dataset: OceanDataset = Depends(get_dataset),
) -> FieldResponse:

    if variable not in FIELD_VARIABLES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported field '{variable}'. "
                f"Supported fields: "
                f"{', '.join(FIELD_VARIABLES)}"
            ),
        )

    dataset_variable = FIELD_VARIABLES[variable]

    # ---------------------------------------------------------------
    # Exact date availability
    # ---------------------------------------------------------------

    if not dataset.has_date(date):
        return FieldResponse(
            variable=variable,
            date=date.isoformat(),
            depth=depth,
            stride=stride,
            points=[],
        )

    # ---------------------------------------------------------------
    # Depth validation
    # ---------------------------------------------------------------

    if dataset_variable in {
        "temperature_mean",
        "salinity_mean",
    } and depth is None:
        raise HTTPException(
            status_code=400,
            detail=f"Depth is required for '{variable}'.",
        )

    if dataset_variable in {
        "tchp",
        "d26",
        "mld",
    }:
        depth = None

    # ---------------------------------------------------------------
    # Extract field
    # ---------------------------------------------------------------

    try:
        field = dataset.field_at(
            variable=dataset_variable,
            date=date,
            depth=depth,
            stride=stride,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    # ---------------------------------------------------------------
    # Convert xarray → API response
    # ---------------------------------------------------------------

    points: list[FieldPoint] = []

    for lat in field.latitude.values:
        for lon in field.longitude.values:

            value = field.sel(
                latitude=lat,
                longitude=lon,
            ).item()

            if value is None:
                numeric_value = None
            else:
                try:
                    numeric_value = float(value)
                except (TypeError, ValueError):
                    numeric_value = None

            points.append(
                FieldPoint(
                    lat=float(lat),
                    lon=float(lon),
                    value=numeric_value,
                    uncertainty=None,
                )
            )

    return FieldResponse(
        variable=variable,
        date=date.isoformat(),
        depth=depth,
        stride=stride,
        points=points,
    )