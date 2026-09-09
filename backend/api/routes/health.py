from fastapi import APIRouter, Depends

from ..dataset import OceanDataset
from ..dependencies import get_dataset
from ..schemas import DatasetStatus


router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("", response_model=DatasetStatus)
def get_health(
    dataset: OceanDataset = Depends(get_dataset),
) -> DatasetStatus:
    summary = dataset.summary()

    return DatasetStatus(
        available=True,
        time_start=summary["time_start"],
        time_end=summary["time_end"],
    )