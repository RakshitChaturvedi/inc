from __future__ import annotations

from datetime import date
from pathlib import Path

from ocean.acquisition.adapters.copernicus import CopernicusAdapter
from ocean.acquisition.models import BoundingBox, DateRange
from ocean.acquisition.request import AcquisitionRequest
from ocean.acquisition.service import AcquisitionService


def main() -> None:
    request = AcquisitionRequest(
        date_range=DateRange(
            start=date(2025, 1, 1),
            end=date(2025, 1, 7),
        ),
        region=BoundingBox(
            lat_min=5.0,
            lat_max=30.0,
            lon_min=45.0,
            lon_max=105.0,
        ),
        variables=(
            "sst",
            "sss",
            "ssh",
            "wind",
            "currents",
        ),
        chunk_days=7,
    )

    sources = {
        "sst": {
            "enabled": True,
            "dataset_id": (
                "METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2"
            ),
            "preferred_variables": (
                "analysed_sst",
            ),
            "output_dir": "data/raw/sst",
        },
        "sss": {
            "enabled": True,
            "dataset_id": (
                "cmems_obs-mob_glo_phy-sss_nrt_multi_P1D"
            ),
            "preferred_variables": (
                "sos",
            ),
            "output_dir": "data/raw/sss",
        },
        "ssh": {
            "enabled": True,
            "dataset_id": (
                "cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.125deg_P1D"
            ),
            "preferred_variables": (
                "sla",
            ),
            "output_dir": "data/raw/ssh",
        },
        "wind": {
            "enabled": True,
            "dataset_id": (
                "cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H"
            ),
            "preferred_variables": (
                "eastward_wind",
                "northward_wind",
                "stress_curl",
            ),
            "output_dir": "data/raw/wind",
        },
        "currents": {
            "enabled": True,
            "dataset_id": (
                "cmems_obs-mob_glo_phy-cur_nrt_"
                "0.25deg_P1D-m"
            ),
            "preferred_variables": (
                "uo",
                "vo",
            ),
            "output_dir": "data/raw/currents",
        },
    }

    output_dir = Path("data/raw/a12_test")

    adapter = CopernicusAdapter(
        sources=sources,
    )

    service = AcquisitionService(
        adapter=adapter,
        output_dir=output_dir,
    )

    manifest = service.acquire(request)

    print("\n" + "=" * 70)
    print("A12 REAL ACQUISITION COMPLETE")
    print("=" * 70)
    print(f"Manifest: {output_dir / 'manifest.json'}")
    print(f"Chunks  : {len(manifest.chunks)}")
    print("=" * 70)


if __name__ == "__main__":
    main()