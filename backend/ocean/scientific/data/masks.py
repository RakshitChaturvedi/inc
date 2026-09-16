import numpy as np
import xarray as xr


def validate_mask_shape(
    mask: xr.DataArray,
    temperature: xr.DataArray,
) -> None:
    expected_dims = (
        "depth",
        "latitude",
        "longitude",
    )

    if mask.dims != expected_dims:
        raise ValueError(
            f"3D mask must use dimensions {expected_dims}, "
            f"got {mask.dims}."
        )

    expected_shape = tuple(
        temperature.sizes[dim]
        for dim in expected_dims
    )

    actual_shape = tuple(
        mask.sizes[dim]
        for dim in expected_dims
    )

    if actual_shape != expected_shape:
        raise ValueError(
            "3D mask shape mismatch: "
            f"expected {expected_shape}, "
            f"got {actual_shape}."
        )


def validate_mask_coordinates(
    mask: xr.DataArray,
    temperature: xr.DataArray,
    *,
    tolerance: float = 1e-6,
) -> None:
    for dim in ("depth", "latitude", "longitude"):
        if dim not in mask.coords:
            raise ValueError(
                f"Mask is missing coordinate: {dim}"
            )

        if dim not in temperature.coords:
            raise ValueError(
                f"Temperature is missing coordinate: {dim}"
            )

        mask_coord = np.asarray(
            mask[dim].values,
            dtype=float,
        )

        temperature_coord = np.asarray(
            temperature[dim].values,
            dtype=float,
        )

        if mask_coord.shape != temperature_coord.shape:
            raise ValueError(
                f"Mask coordinate shape mismatch for {dim}: "
                f"expected {temperature_coord.shape}, "
                f"got {mask_coord.shape}."
            )

        if not np.allclose(
            mask_coord,
            temperature_coord,
            atol=tolerance,
            rtol=0.0,
        ):
            raise ValueError(
                f"Mask {dim} coordinates do not match "
                "the scientific dataset."
            )


def align_mask(
    mask: xr.DataArray,
) -> xr.DataArray:
    return mask.transpose(
        "depth",
        "latitude",
        "longitude",
    )