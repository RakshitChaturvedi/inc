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


import numpy as np

FIELD_VARIABLES = {
    "temperature": "temperature_mean",
    "salinity": "salinity_mean",
    "uncertainty": "temperature_std",
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
    # Date availability check
    # ---------------------------------------------------------------

    if len(dataset.available_times()) == 0:
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
        "temperature_std",
    }:
        if depth is None:
            depth = 0.0

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
    # Convert xarray → API response (fast vectorized access)
    # ---------------------------------------------------------------

    points: list[FieldPoint] = []
    lats = field.latitude.values
    lons = field.longitude.values
    vals = field.values

    for i, lat in enumerate(lats):
        lat_f = float(lat)
        row = vals[i]
        for j, lon in enumerate(lons):
            v = row[j]
            numeric_value = float(v) if np.isfinite(v) else None
            points.append(
                FieldPoint(
                    lat=lat_f,
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