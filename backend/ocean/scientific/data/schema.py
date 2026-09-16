from dataclasses import dataclass
from typing import Final

TEMPERATURE: Final[str] = "temperature_mean"
SALINITY: Final[str] = "salinity_mean"

TEMPERATURE_STD: Final[str] = "temperature_std"
SALINITY_STD: Final[str] = "salinity_std"

TIME: Final[str] = "time"
DEPTH: Final[str] = "depth"
LATITUDE: Final[str] = "latitude"
LONGITUDE: Final[str] = "longitude"

EXPECTED_DEPTHS_M: Final[tuple[float, ...]] = (
    0.0, 5.0, 10.0, 20.0, 30.0, 50.0, 75.0, 100.0,
    125.0, 150.0, 200.0, 300.0, 500.0, 700.0, 1000.0,
)

LAT_MIN: Final[float] = 5.0
LAT_MAX: Final[float] = 30.0
LON_MIN: Final[float] = 45.0
LON_MAX: Final[float] = 105.0

GRID_RESOLUTION_DEG: Final[float] = 0.25
OCEAN_MASK_3D: Final[str] = "ocean_mask_3d"

@dataclass(frozen=True)
class ScientificSchema:
    temperature_name: str = TEMPERATURE
    salinity_name: str = SALINITY

    temperature_std_name: str = TEMPERATURE_STD
    salinity_std_name: str = SALINITY_STD

    time_dim: str = TIME
    depth_dim: str = DEPTH
    latitude_dim: str = LATITUDE
    longitude_dim: str = LONGITUDE

    expected_depths_m: tuple[float, ...] = EXPECTED_DEPTHS_M

    lat_min: float = LAT_MIN
    lat_max: float = LAT_MAX
    lon_min: float = LON_MIN
    lon_max: float = LON_MAX

    mask_name: str = OCEAN_MASK_3D
    resolution_deg: float = GRID_RESOLUTION_DEG