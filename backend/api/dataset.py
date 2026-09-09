from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any
from functools import lru_cache

import numpy as np
import xarray as xr

from .errors import DatasetUnavailableError


import json
import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("OCEAN_DATA_DIR", BACKEND_ROOT / "data"))

BUSINESS_DIR = DATA_DIR / "business"
EVALUATION_DIR = DATA_DIR / "evaluation"
PHYSICS_DIR = DATA_DIR / "physics"

DASHBOARD_DATASET_PATH = DASHBOARD_PATH = Path(
    os.getenv(
        "DASHBOARD_DATASET_PATH",
        os.getenv("OCEAN_DASHBOARD_PATH", BUSINESS_DIR / "dashboard_ready.nc"),
    )
)
PHYSICS_ADJUSTED_PATH = Path(
    os.getenv("PHYSICS_ADJUSTED_PATH", PHYSICS_DIR / "physics_adjusted.nc")
)
EVALUATION_REPORT_PATH = Path(
    os.getenv(
        "EVALUATION_REPORT_PATH",
        os.getenv("OCEAN_EVALUATION_REPORT_PATH", EVALUATION_DIR / "evaluation_report.json"),
    )
)


# ---------------------------------------------------------------------------
# Dataset configuration
# ---------------------------------------------------------------------------

EXPECTED_DIMS = (
    "time",
    "depth",
    "latitude",
    "longitude",
)

BUSINESS_VARIABLES = (
    "temperature_mean",
    "temperature_std",
    "salinity_mean",
    "salinity_std",
    "tchp",
    "d26",
    "mld",
    "thermocline_depth",
)


@dataclass(frozen=True)
class GridInfo:
    depth: np.ndarray
    latitude: np.ndarray
    longitude: np.ndarray

@lru_cache(maxsize=1)
def get_dashboard_dataset() -> xr.Dataset:
    """
    Open and cache the dashboard-ready OceanEmbed dataset.

    The dataset is opened lazily. Individual routes select only the
    requested date / depth / coordinate before loading values.
    """

    if not DASHBOARD_DATASET_PATH.exists():
        raise DatasetUnavailableError(
            f"Dashboard dataset not found: {DASHBOARD_DATASET_PATH}"
        )

    try:
        return xr.open_dataset(DASHBOARD_DATASET_PATH)
    except Exception as exc:
        raise DatasetUnavailableError(
            f"Failed to open dashboard dataset: {exc}"
        ) from exc

class OceanDataset:
    """
    Shared read-only access to OceanEmbed NetCDF artifacts.

    Routes should use this class instead of opening NetCDF files directly.
    """

    def __init__(
        self,
        dashboard_path: Path = DASHBOARD_PATH,
        physics_path: Path = PHYSICS_ADJUSTED_PATH,
        evaluation_report_path: Path = EVALUATION_REPORT_PATH,
    ) -> None:
        self.dashboard_path = dashboard_path
        self.physics_path = physics_path
        self.evaluation_report_path = evaluation_report_path

        self._dashboard: xr.Dataset | None = None
        self._physics: xr.Dataset | None = None

        self._lock = Lock()

    # ------------------------------------------------------------------
    # Dataset loading
    # ------------------------------------------------------------------

    @property
    def dashboard(self) -> xr.Dataset:
        if self._dashboard is None:
            with self._lock:
                if self._dashboard is None:
                    self._dashboard = xr.open_dataset(
                        self.dashboard_path
                    )

        return self._dashboard

    @property
    def physics(self) -> xr.Dataset:
        if self._physics is None:
            with self._lock:
                if self._physics is None:
                    self._physics = xr.open_dataset(
                        self.physics_path
                    )

        return self._physics

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        if self._dashboard is not None:
            self._dashboard.close()
            self._dashboard = None

        if self._physics is not None:
            self._physics.close()
            self._physics = None

    # ------------------------------------------------------------------
    # Dataset status
    # ------------------------------------------------------------------

    @property
    def dashboard_available(self) -> bool:
        return self.dashboard_path.exists()

    @property
    def physics_available(self) -> bool:
        return self.physics_path.exists()

    @property
    def evaluation_report_available(self) -> bool:
        return self.evaluation_report_path.exists()

    @property
    def evaluation_report(self) -> dict | None:
        if not self.evaluation_report_available:
            return None
        try:
            with open(self.evaluation_report_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Coordinates
    # ------------------------------------------------------------------

    @property
    def time(self) -> xr.DataArray:
        return self.dashboard["time"]

    @property
    def depth(self) -> xr.DataArray:
        return self.dashboard["depth"]

    @property
    def latitude(self) -> xr.DataArray:
        return self.dashboard["latitude"]

    @property
    def longitude(self) -> xr.DataArray:
        return self.dashboard["longitude"]

    @property
    def grid(self) -> GridInfo:
        return GridInfo(
            depth=self.depth.values,
            latitude=self.latitude.values,
            longitude=self.longitude.values,
        )

    # ------------------------------------------------------------------
    # Dimensions
    # ------------------------------------------------------------------

    @property
    def dimensions(self) -> dict[str, int]:
        return {
            key: int(value)
            for key, value in self.dashboard.sizes.items()
        }

    # ------------------------------------------------------------------
    # Variables
    # ------------------------------------------------------------------

    def has_variable(self, variable: str) -> bool:
        return variable in self.dashboard.data_vars

    def require_variable(self, variable: str) -> xr.DataArray:
        if variable not in self.dashboard.data_vars:
            raise KeyError(
                f"Dataset does not contain variable '{variable}'."
            )

        return self.dashboard[variable]

    # ------------------------------------------------------------------
    # Date handling
    # ------------------------------------------------------------------

    def available_times(self) -> np.ndarray:
        return self.time.values

    def has_date(self, date: Any) -> bool:
        target = np.datetime64(date, "ns")

        times = self.time.values.astype("datetime64[ns]")

        return bool(np.any(times == target))

    def nearest_time(self, date: Any) -> np.datetime64:
        target = np.datetime64(date, "ns")

        times = self.time.values.astype("datetime64[ns]")

        index = int(
            np.argmin(
                np.abs(times - target)
            )
        )

        return times[index]

    # ------------------------------------------------------------------
    # Grid handling
    # ------------------------------------------------------------------

    def nearest_latitude(self, latitude: float) -> float:
        values = self.latitude.values.astype(float)

        index = int(
            np.argmin(
                np.abs(values - latitude)
            )
        )

        return float(values[index])

    def nearest_longitude(self, longitude: float) -> float:
        values = self.longitude.values.astype(float)

        index = int(
            np.argmin(
                np.abs(values - longitude)
            )
        )

        return float(values[index])

    def nearest_depth(self, depth: float) -> float:
        values = self.depth.values.astype(float)

        index = int(
            np.argmin(
                np.abs(values - depth)
            )
        )

        return float(values[index])

    def nearest_grid_cell(
        self,
        latitude: float,
        longitude: float,
    ) -> tuple[float, float]:
        return (
            self.nearest_latitude(latitude),
            self.nearest_longitude(longitude),
        )

    # ------------------------------------------------------------------
    # Point extraction
    # ------------------------------------------------------------------

    def value_at(
        self,
        variable: str,
        date: Any,
        latitude: float,
        longitude: float,
        depth: float | None = None,
    ) -> float | None:

        data = self.require_variable(variable)

        time_value = self.nearest_time(date)
        lat_value = self.nearest_latitude(latitude)
        lon_value = self.nearest_longitude(longitude)

        selector: dict[str, Any] = {
            "time": time_value,
            "latitude": lat_value,
            "longitude": lon_value,
        }

        if "depth" in data.dims:
            if depth is None:
                raise ValueError(
                    f"Variable '{variable}' requires a depth."
                )

            selector["depth"] = self.nearest_depth(depth)

        try:
            value = data.sel(
                selector,
                method="nearest",
            ).item()
        except (KeyError, ValueError, IndexError):
            return None

        if value is None:
            return None

        try:
            value = float(value)
        except (TypeError, ValueError):
            return None

        if not np.isfinite(value):
            return None

        return value

    # ------------------------------------------------------------------
    # Profile extraction
    # ------------------------------------------------------------------

    def profile_at(
        self,
        variable: str,
        date: Any,
        latitude: float,
        longitude: float,
    ) -> tuple[float, float, list[tuple[float, float | None]]]:

        data = self.require_variable(variable)

        if "depth" not in data.dims:
            raise ValueError(
                f"Variable '{variable}' is not depth-dependent."
            )

        time_value = self.nearest_time(date)
        lat_value = self.nearest_latitude(latitude)
        lon_value = self.nearest_longitude(longitude)

        selected = data.sel(
            {
                "time": time_value,
                "latitude": lat_value,
                "longitude": lon_value,
            },
            method="nearest",
        )

        values = selected.values

        profile: list[tuple[float, float | None]] = []

        for depth, value in zip(
            self.depth.values,
            values,
        ):
            if np.isfinite(value):
                profile.append(
                    (
                        float(depth),
                        float(value),
                    )
                )
            else:
                profile.append(
                    (
                        float(depth),
                        None,
                    )
                )

        return (
            float(lat_value),
            float(lon_value),
            profile,
        )

    # ------------------------------------------------------------------
    # Field extraction
    # ------------------------------------------------------------------

    def field_at(
        self,
        variable: str,
        date: Any,
        depth: float | None = None,
        stride: int = 1,
    ) -> xr.DataArray:

        data = self.require_variable(variable)

        time_value = self.nearest_time(date)

        selector: dict[str, Any] = {
            "time": time_value,
        }

        if "depth" in data.dims:
            if depth is None:
                raise ValueError(
                    f"Variable '{variable}' requires depth."
                )

            selector["depth"] = self.nearest_depth(depth)

        selected = data.sel(
            selector,
            method="nearest",
        )

        if stride > 1:
            selected = selected.isel(
                latitude=slice(None, None, stride),
                longitude=slice(None, None, stride),
            )

        return selected

    # ------------------------------------------------------------------
    # Dataset metadata
    # ------------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        return {
            "dimensions": self.dimensions,
            "variables": list(self.dashboard.data_vars),
            "time_start": str(self.time.values[0]),
            "time_end": str(self.time.values[-1]),
            "depths": [
                float(value)
                for value in self.depth.values
            ],
            "latitude_range": [
                float(self.latitude.values.min()),
                float(self.latitude.values.max()),
            ],
            "longitude_range": [
                float(self.longitude.values.min()),
                float(self.longitude.values.max()),
            ],
        }


dataset = OceanDataset()