from __future__ import annotations

import xarray as xr


def harmonize_sst(ds: xr.Dataset) -> xr.Dataset:
    if "analysed_sst" not in ds:
        raise ValueError(
            "SST variable 'analysed_sst' not found."
        )

    ds = ds.rename({
        "analysed_sst": "sst",
    })

    return ds[["sst"]]


def harmonize_sss(ds: xr.Dataset) -> xr.Dataset:
    if "sos" not in ds:
        raise ValueError(
            "SSS variable 'sos' not found."
        )
    ds=ds.rename({"sos": "sss"})
    return ds[["sss"]]


def harmonize_ssh(ds: xr.Dataset) -> xr.Dataset:
    if "sla" not in ds:
        raise ValueError(
            "SSH variable 'sla' not found."
        )

    ds = ds.rename({
        "sla": "ssh",
    })

    return ds[["ssh"]]


def harmonize_wind(ds: xr.Dataset) -> xr.Dataset:
    required = {"eastward_wind", "northward_wind"}
    missing = required - set(ds.data_vars)

    if missing:
        raise ValueError(
            f"Wind dataset missing variables: {sorted(missing)}"
        )

    ds = ds.rename({
        "eastward_wind": "wind_u",
        "northward_wind": "wind_v",
    })

    variables = [
        "wind_u",
        "wind_v",
    ]

    # Do NOT use the source `ws` here.
    # wind_speed will be derived after daily averaging.
    if "wind_speed" in ds:
        variables.append("wind_speed")

    return ds[["wind_u", "wind_v"]]


def harmonize_currents(ds: xr.Dataset) -> xr.Dataset:
    required = {"uo", "vo"}
    missing = required - set(ds.data_vars)

    if missing:
        raise ValueError(
            f"Current dataset missing variables: {sorted(missing)}"
        )

    ds = ds.rename({
        "uo": "current_u",
        "vo": "current_v",
    })

    return ds[
        [
            "current_u",
            "current_v",
        ]
    ]


def harmonize_subsurface(
    ds: xr.Dataset,
    *,
    temperature_name: str,
    salinity_name: str,
) -> xr.Dataset:

    required = {
        temperature_name,
        salinity_name,
    }

    missing = required - set(ds.data_vars)

    if missing:
        raise ValueError(
            f"Subsurface dataset missing variables: {sorted(missing)}"
        )

    ds = ds.rename({
        temperature_name: "temperature",
        salinity_name: "salinity",
    })

    return ds[
        [
            "temperature",
            "salinity",
        ]
    ]


def finalize_dataset(
    ds: xr.Dataset,
    *,
    dataset_name: str,
    spatial_cfg: dict | None = None,
) -> xr.Dataset:

    ds = ds.sortby("time")
    ds = ds.sortby("latitude")
    ds = ds.sortby("longitude")

    ds.attrs["oceanembed_dataset"] = dataset_name
    ds.attrs["oceanembed_phase"] = "phase2"
    ds.attrs["oceanembed_temporal_resolution"] = "daily"

    if spatial_cfg is not None:
        ds.attrs["oceanembed_spatial_domain"] = (
            f"{spatial_cfg['lat_min']}N-"
            f"{spatial_cfg['lat_max']}N, "
            f"{spatial_cfg['lon_min']}E-"
            f"{spatial_cfg['lon_max']}E"
        )

        ds.attrs["oceanembed_spatial_resolution"] = (
            f"{spatial_cfg['resolution']}deg"
        )

    return ds