from __future__ import annotations

import copernicusmarine


DATASETS = {
    "sst": "METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2",
    "sss": "cmems_obs-mob_glo_phy-sss_nrt_multi_P1D",
    "ssh": "cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.25deg_P1D",
    "wind": "cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H",
    "currents": "cmems_obs-mob_glo_phy-cur_nrt_0.25deg_P1D-m",
}


for name, dataset_id in DATASETS.items():

    print(f"\n{name.upper()}")

    catalog = copernicusmarine.describe(
        dataset_id=dataset_id,
        disable_progress_bar=True,
    )

    dataset = catalog.products[0].datasets[0]

    variables = set()

    for version in dataset.versions:
        for part in version.parts:
            for service in part.services:
                for variable in service.variables:
                    variables.add(variable.short_name)

    print("dataset :", dataset.dataset_id)
    print("version :", dataset.versions[0].label)
    print("variables:", sorted(variables))