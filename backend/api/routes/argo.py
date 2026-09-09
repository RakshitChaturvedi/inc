from __future__ import annotations

from fastapi import APIRouter, Query

from ..schemas import ArgoFloatResponse

router = APIRouter(
    prefix="/argo",
    tags=["argo"],
)

ARGO_FLOATS: list[ArgoFloatResponse] = [
    ArgoFloatResponse(lat=11.25, lon=70.75, id="WMO 2900", lastProfile="2026-W35"),
    ArgoFloatResponse(lat=15.75, lon=84.25, id="WMO 2901", lastProfile="2026-W35"),
    ArgoFloatResponse(lat=18.50, lon=89.50, id="WMO 2902", lastProfile="2026-W35"),
    ArgoFloatResponse(lat=21.25, lon=93.75, id="WMO 2903", lastProfile="2026-W35"),
    ArgoFloatResponse(lat=9.75, lon=59.50, id="WMO 2904", lastProfile="2026-W35"),
    ArgoFloatResponse(lat=13.25, lon=77.50, id="WMO 2905", lastProfile="2026-W35"),
    ArgoFloatResponse(lat=23.50, lon=64.25, id="WMO 2906", lastProfile="2026-W35"),
    ArgoFloatResponse(lat=17.75, lon=100.25, id="WMO 2907", lastProfile="2026-W35"),
]


@router.get("", response_model=list[ArgoFloatResponse])
def get_argo(
    date: str | None = Query(None),
    week: str | None = Query(None),
) -> list[ArgoFloatResponse]:
    return ARGO_FLOATS
