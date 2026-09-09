from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr


def _daily_index(
    start: str,
    end: str,
) -> pd.DatetimeIndex:
    return pd.date_range(
        start=start,
        end=end,
        freq="1D",
    )

def deduplicate_time(ds: xr.Dataset) -> xr.Dataset:
    """
    Remove duplicate timestamps, keeping the first occurrence.
    """
    _, unique_indices = np.unique(
        ds["time"].values,
        return_index=True,
    )

    return ds.isel(
        time=np.sort(unique_indices)
    )

def daily_mean(
    ds: xr.Dataset,
) -> xr.Dataset:
    """
    Aggregate sub-daily data to daily means.

    Used primarily for CCMP wind.
    """

    if "time" not in ds.coords:
        raise ValueError(
            "Dataset has no time coordinate."
        )

    return ds.resample(
        time="1D"
    ).mean(
        keep_attrs=True
    )


def align_daily(
    ds: xr.Dataset,
    *,
    start: str,
    end: str,
) -> xr.Dataset:
    """
    Align data to the requested daily timeline.

    Existing daily values are retained. For coarser products such as
    weekly SSS, temporal interpolation fills the daily timeline.

    This function should NOT be used for sub-daily wind data; use
    daily_mean() first.
    """

    target = _daily_index(
        start,
        end,
    )

    if ds.sizes.get("time", 0) == 0:
        raise ValueError(
            "Cannot align dataset with empty time dimension."
        )

    # Interpolation requires numeric/datetime-compatible time.
    ds = ds.sortby("time")

    source_start = pd.Timestamp(
        ds.time.values[0]
    )
    source_end = pd.Timestamp(
        ds.time.values[-1]
    )

    target_start = target[0]
    target_end = target[-1]

    if source_start > target_start:
        raise ValueError(
            f"Dataset starts at {source_start}, "
            f"after requested range {target_start}."
        )

    if source_end < target_end:
        raise ValueError(
            f"Dataset ends at {source_end}, "
            f"before requested range {target_end}."
        )

    return ds.interp(
        time=target,
        method="linear",
    )


def derive_wind_speed(
    ds: xr.Dataset,
) -> xr.Dataset:
    """
    Derive wind speed from the daily-mean vector components.
    """

    required = {"wind_u", "wind_v"}

    missing = required - set(ds.data_vars)

    if missing:
        raise ValueError(
            f"Cannot derive wind speed. Missing: {sorted(missing)}"
        )

    ds["wind_speed"] = np.sqrt(
        ds["wind_u"] ** 2
        + ds["wind_v"] ** 2
    )

    ds["wind_speed"].attrs.update(
        {
            "long_name": "Wind speed derived from daily mean components",
            "units": "m s-1",
        }
    )

    return ds