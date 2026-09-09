from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..dataset import OceanDataset
from ..dependencies import get_dataset

router = APIRouter(
    prefix="/evaluation",
    tags=["evaluation"],
)


@router.get("")
def get_evaluation_report(
    dataset: OceanDataset = Depends(get_dataset),
) -> dict:
    report = dataset.evaluation_report
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"Evaluation report not found at {dataset.evaluation_report_path}",
        )
    return report
