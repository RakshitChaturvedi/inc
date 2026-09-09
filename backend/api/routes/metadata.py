from fastapi import APIRouter, Depends

from ..dataset import OceanDataset
from ..dependencies import get_dataset


router = APIRouter(
    prefix="/metadata",
    tags=["metadata"],
)


@router.get("")
def get_metadata(
    dataset: OceanDataset = Depends(get_dataset),
) -> dict:
    summary = dataset.summary()

    return {
        "dimensions": summary["dimensions"],
        "variables": summary["variables"],
        "time_start": summary["time_start"],
        "time_end": summary["time_end"],
        "depths": summary["depths"],
        "latitude_range": summary["latitude_range"],
        "longitude_range": summary["longitude_range"],
        "grid_resolution": 0.25,
    }