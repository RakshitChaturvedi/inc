# backend/api/coordinates.py

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# OceanEmbed model domain
# ---------------------------------------------------------------------------

MIN_LAT = 5.0
MAX_LAT = 30.0

MIN_LON = 45.0
MAX_LON = 105.0

LAT_STEP = 0.25
LON_STEP = 0.25


@dataclass(frozen=True)
class ModelCoordinate:
    lat: float
    lon: float


# ---------------------------------------------------------------------------
# Coordinate validation
# ---------------------------------------------------------------------------

def validate_coordinates(lat: float, lon: float) -> None:
    """
    Validate that a coordinate lies inside the OceanEmbed model domain.

    This only validates geographic bounds.

    Land/ocean classification is handled separately by the land mask.
    """

    if not MIN_LAT <= lat <= MAX_LAT:
        raise ValueError(
            f"Latitude {lat} is outside the OceanEmbed domain "
            f"[{MIN_LAT}, {MAX_LAT}]"
        )

    if not MIN_LON <= lon <= MAX_LON:
        raise ValueError(
            f"Longitude {lon} is outside the OceanEmbed domain "
            f"[{MIN_LON}, {MAX_LON}]"
        )


# ---------------------------------------------------------------------------
# Model-grid resolution
# ---------------------------------------------------------------------------

def get_nearest_model_cell(
    lat: float,
    lon: float,
) -> ModelCoordinate:
    """
    Resolve an arbitrary valid coordinate to the nearest OceanEmbed
    0.25-degree model grid cell.
    """

    validate_coordinates(lat, lon)

    nearest_lat = round(lat / LAT_STEP) * LAT_STEP
    nearest_lon = round(lon / LON_STEP) * LON_STEP

    nearest_lat = max(MIN_LAT, min(MAX_LAT, nearest_lat))
    nearest_lon = max(MIN_LON, min(MAX_LON, nearest_lon))

    return ModelCoordinate(
        lat=round(nearest_lat, 2),
        lon=round(nearest_lon, 2),
    )


def is_model_coordinate(lat: float, lon: float) -> bool:
    """
    Return whether a coordinate lies exactly on the model grid.
    """

    if not (
        MIN_LAT <= lat <= MAX_LAT
        and MIN_LON <= lon <= MAX_LON
    ):
        return False

    lat_index = (lat - MIN_LAT) / LAT_STEP
    lon_index = (lon - MIN_LON) / LON_STEP

    return (
        abs(lat_index - round(lat_index)) < 1e-6
        and abs(lon_index - round(lon_index)) < 1e-6
    )