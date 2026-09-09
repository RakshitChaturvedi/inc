from fastapi import APIRouter, Depends

from ..dataset import OceanDataset
from ..dependencies import get_dataset
from ..schemas import RunStatusResponse


router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("", response_model=RunStatusResponse)
def get_health(
    dataset: OceanDataset = Depends(get_dataset),
) -> RunStatusResponse:
    available = dataset.dashboard_available
    start_str = "27 Aug"
    end_str = "02 Sep 2026"
    
    if available:
        try:
            summary = dataset.summary()
            if summary.get("time_start") and summary.get("time_end"):
                start_str = str(summary["time_start"])[:10]
                end_str = str(summary["time_end"])[:10]
        except Exception:
            pass

    last_updated = "03 Sep 2026 · 06:18 UTC"
    if dataset.evaluation_report_available and dataset.evaluation_report:
        ts = dataset.evaluation_report.get("timestamp")
        if ts:
            last_updated = str(ts)

    return RunStatusResponse(
        analysisWeek="2026-W35",
        modelVersion="oceanembed-v1.0.0",
        gateStatus="published" if available else "blocked",
        sourceWindow=f"{start_str} – {end_str}",
        lastUpdated=last_updated,
    )