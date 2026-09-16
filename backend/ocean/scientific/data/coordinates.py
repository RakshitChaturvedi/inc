import numpy as np


def validate_regular_grid(
    latitude,
    longitude,
    *,
    resolution: float = 0.25,
    tolerance: float = 1e-6,
) -> None:
    lat = np.asarray(latitude)
    lon = np.asarray(longitude)

    if lat.ndim != 1 or lon.ndim != 1:
        raise ValueError("Latitude and longitude must be 1D coordinates.")

    if len(lat) < 2 or len(lon) < 2:
        raise ValueError("Latitude/longitude coordinates are too short.")

    lat_spacing = np.diff(lat)
    lon_spacing = np.diff(lon)

    if not np.allclose(lat_spacing, resolution, atol=tolerance):
        raise ValueError("Latitude grid is not the expected 0.25° grid.")

    if not np.allclose(lon_spacing, resolution, atol=tolerance):
        raise ValueError("Longitude grid is not the expected 0.25° grid.")

def validate_domain(
        latitude, longitude,
        *,
        lat_min=5.0, lat_max=30.0,
        lon_min=45.0, lon_max=105.0
) -> None:
    if not np.isclose(latitude[0], lat_min):
        raise ValueError("Unexpected latitude lower bound.")

    if not np.isclose(latitude[-1], lat_max):
        raise ValueError("Unexpected latitude upper bound.")

    if not np.isclose(longitude[0], lon_min):
        raise ValueError("Unexpected longitude lower bound.")

    if not np.isclose(longitude[-1], lon_max):
        raise ValueError("Unexpected longitude upper bound.")

def validate_depths(
    depth,
    expected_depths,
    *,
    tolerance=1e-6,
) -> None:
    depth = np.asarray(depth, dtype=float)
    expected = np.asarray(expected_depths, dtype=float)

    if depth.shape != expected.shape:
        raise ValueError(
            f"Expected {len(expected)} depth levels, "
            f"got {len(depth)}."
        )

    if not np.allclose(depth, expected, atol=tolerance):
        raise ValueError(
            f"Depth coordinate does not match expected levels.\n"
            f"Expected: {expected.tolist()}\n"
            f"Actual:   {depth.tolist()}"
        )