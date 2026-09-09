from __future__ import annotations

from pathlib import Path

import yaml

from .copernicus import acquire_copernicus
from .podaac import acquire_podaac


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:

    config_path = ROOT / "config" / "acquisition.yaml"

    with config_path.open() as f:
        cfg = yaml.safe_load(f)

    print("=" * 70)
    print("OceanEmbed Backend — Data Acquisition")
    print("=" * 70)

    print(
        f"Date range : "
        f"{cfg['dates']['start']} -> {cfg['dates']['end']}"
    )

    print(
        f"Domain     : "
        f"{cfg['domain']['lat_min']} -> "
        f"{cfg['domain']['lat_max']} N, "
        f"{cfg['domain']['lon_min']} -> "
        f"{cfg['domain']['lon_max']} E"
    )

    print(
        f"Resolution : {cfg['resolution']}°"
    )

    Path(cfg["output_root"]).mkdir(
        parents=True,
        exist_ok=True,
    )

    acquire_copernicus(cfg)
    acquire_podaac(cfg)

    print("\n" + "=" * 70)
    print("DATA ACQUISITION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()