from __future__ import annotations

import copernicusmarine


DATASETS = {
    "sst": "METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2",
    "sss": "cmems_obs-mob_glo_phy-sss_nrt_multi_P1D",
    "ssh": "cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.25deg_P1D",
    "wind": "cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H",
    "currents": "cmems_obs-mob_glo_phy-cur_nrt_0.25deg_P1D-m",
}


def inspect_dataset(name: str, dataset_id: str) -> None:
    print(f"\n{name.upper()}")
    print("-" * 60)

    catalog = copernicusmarine.describe(
        dataset_id=dataset_id,
        disable_progress_bar=True,
    )

    if not catalog.products:
        print("ERROR: dataset not found")
        return

    dataset = catalog.products[0].datasets[0]

    print(f"Dataset : {dataset.dataset_id}")

    for version in dataset.versions:
        print(f"Version : {version.label}")

        for part in version.parts:
            # Time coverage
            coordinates = part.get_coordinates()

            time_coords = coordinates.get("time", [])

            if time_coords:
                time = time_coords[0]
                print(f"Time    : {time.minimum_value} -> {time.maximum_value}")
            else:
                print("Time    : unavailable")

            # Spatial coordinates
            for axis in ("latitude", "longitude"):
                coords = coordinates.get(axis, [])

                if coords:
                    coord = coords[0]

                    print(
                        f"{axis.capitalize():8}: "
                        f"{coord.minimum_value} -> "
                        f"{coord.maximum_value} "
                        f"(step={coord.step})"
                    )

            # Variables
            variables = []

            for service in part.services:
                for variable in service.variables:
                    if variable.short_name not in variables:
                        variables.append(variable.short_name)

            print(f"Variables: {', '.join(variables)}")


def main() -> None:
    for name, dataset_id in DATASETS.items():
        try:
            inspect_dataset(name, dataset_id)
        except Exception as exc:
            print(f"\n{name.upper()} FAILED")
            print(f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()