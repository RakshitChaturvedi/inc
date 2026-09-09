from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from .thermocline import (
    calculate_thermocline_depth,
    calculate_thermocline,
)


# ---------------------------------------------------------------------------
# Test 1 — Basic maximum-gradient detection
# ---------------------------------------------------------------------------

def test_maximum_gradient_detection():
    depths = np.array(
        [0, 5, 10, 20, 30],
        dtype=np.float32,
    )

    # Largest gradient is between 10 m and 20 m:
    #
    # 0 -> 5  : 0.2
    # 5 -> 10 : 0.2
    # 10 -> 20: 2.0   <-- maximum
    # 20 -> 30: 0.1
    temperature = np.array(
        [
            30.0,
            29.0,
            28.0,
            8.0,
            7.0,
        ],
        dtype=np.float32,
    )

    result = calculate_thermocline_depth(
        temperature,
        depths,
    )

    # Midpoint of 10 and 20 m.
    assert result == pytest.approx(15.0)


# ---------------------------------------------------------------------------
# Test 2 — Irregular depth spacing is handled correctly
# ---------------------------------------------------------------------------

def test_irregular_depth_spacing():
    depths = np.array(
        [0, 5, 10, 20, 100],
        dtype=np.float32,
    )

    # Raw temperature differences:
    #
    # 0-5     : 1
    # 5-10    : 1
    # 10-20   : 5
    # 20-100  : 20
    #
    # But gradients are:
    #
    # 0-5     : 0.20
    # 5-10    : 0.20
    # 10-20   : 0.50  <-- maximum
    # 20-100  : 0.25
    #
    # This test ensures we divide by dz.

    temperature = np.array(
        [
            30.0,
            29.0,
            28.0,
            23.0,
            3.0,
        ],
        dtype=np.float32,
    )

    result = calculate_thermocline_depth(
        temperature,
        depths,
    )

    assert result == pytest.approx(15.0)


# ---------------------------------------------------------------------------
# Test 3 — NaN levels
# ---------------------------------------------------------------------------

def test_nan_levels():
    depths = np.array(
        [0, 5, 10, 20, 30],
        dtype=np.float32,
    )

    temperature = np.array(
        [
            30.0,
            np.nan,
            28.0,
            20.0,
            19.0,
        ],
        dtype=np.float32,
    )

    result = calculate_thermocline_depth(
        temperature,
        depths,
    )

    # The 5-10 m interval is invalid because one endpoint is NaN.
    # The strongest valid gradient is 10-20 m.
    assert result == pytest.approx(15.0)


# ---------------------------------------------------------------------------
# Test 4 — Insufficient valid levels
# ---------------------------------------------------------------------------

def test_insufficient_valid_levels():
    depths = np.array(
        [0, 5, 10, 20, 30],
        dtype=np.float32,
    )

    temperature = np.array(
        [
            30.0,
            np.nan,
            np.nan,
            20.0,
            np.nan,
        ],
        dtype=np.float32,
    )

    result = calculate_thermocline_depth(
        temperature,
        depths,
        min_valid_levels=3,
    )

    assert np.isnan(result)


# ---------------------------------------------------------------------------
# Test 5 — Completely invalid column
# ---------------------------------------------------------------------------

def test_completely_invalid_column():
    depths = np.array(
        [0, 5, 10, 20],
        dtype=np.float32,
    )

    temperature = np.array(
        [np.nan, np.nan, np.nan, np.nan],
        dtype=np.float32,
    )

    result = calculate_thermocline_depth(
        temperature,
        depths,
    )

    assert np.isnan(result)


# ---------------------------------------------------------------------------
# Test 6 — Flat temperature profile
# ---------------------------------------------------------------------------

def test_flat_temperature_profile():
    depths = np.array(
        [0, 5, 10, 20, 30],
        dtype=np.float32,
    )

    temperature = np.full(
        5,
        25.0,
        dtype=np.float32,
    )

    result = calculate_thermocline_depth(
        temperature,
        depths,
    )

    # There is no actual thermocline.
    #
    # Since all gradients are zero, the implementation's argmax
    # convention selects the first valid interval.
    assert result == pytest.approx(2.5)


# ---------------------------------------------------------------------------
# Test 7 — Multiple profiles
# ---------------------------------------------------------------------------

def test_multiple_profiles():
    depths = np.array(
        [0, 5, 10, 20, 30],
        dtype=np.float32,
    )

    temperature = np.array(
        [
            [
                30.0,
                29.0,
                28.0,
                10.0,
                9.0,
            ],
            [
                28.0,
                27.0,
                20.0,
                19.0,
                18.0,
            ],
        ],
        dtype=np.float32,
    )

    result = calculate_thermocline_depth(
        temperature,
        depths,
    )

    assert result.shape == (2,)

    # Profile 1:
    # maximum gradient = 10-20 m
    assert result[0] == pytest.approx(15.0)

    # Profile 2:
    # maximum gradient = 5-10 m
    assert result[1] == pytest.approx(7.5)


# ---------------------------------------------------------------------------
# Test 8 — Xarray wrapper
# ---------------------------------------------------------------------------

def test_xarray_wrapper():
    depths = np.array(
        [0, 5, 10, 20, 30],
        dtype=np.float32,
    )

    temperature = xr.DataArray(
        np.array(
            [
                [
                    [30.0, 29.0, 28.0, 10.0, 9.0],
                    [28.0, 27.0, 20.0, 19.0, 18.0],
                ]
            ],
            dtype=np.float32,
        ),
        dims=("time", "latitude", "depth"),
        coords={
            "time": [np.datetime64("2021-01-01")],
            "latitude": [10.0, 11.0],
            "depth": depths,
        },
        name="temperature_mean",
    )

    result = calculate_thermocline(
        temperature,
        depth_dim="depth",
    )

    assert result.name == "thermocline_depth"
    assert result.dims == ("time", "latitude")
    assert result.shape == (1, 2)

    assert result.values[0, 0] == pytest.approx(15.0)
    assert result.values[0, 1] == pytest.approx(7.5)


# ---------------------------------------------------------------------------
# Test 9 — Invalid depth dimension
# ---------------------------------------------------------------------------

def test_invalid_depth_dimension():
    temperature = xr.DataArray(
        np.ones((2, 3)),
        dims=("latitude", "depth"),
        coords={
            "latitude": [10.0, 11.0],
            "depth": [0.0, 10.0, 20.0],
        },
    )

    with pytest.raises(ValueError):
        calculate_thermocline(
            temperature,
            depth_dim="pressure",
        )


# ---------------------------------------------------------------------------
# Test 10 — Depth mismatch
# ---------------------------------------------------------------------------

def test_depth_mismatch():
    depths = np.array(
        [0, 5, 10, 20],
        dtype=np.float32,
    )

    temperature = np.ones(
        5,
        dtype=np.float32,
    )

    with pytest.raises(ValueError):
        calculate_thermocline_depth(
            temperature,
            depths,
        )


# ---------------------------------------------------------------------------
# Test 11 — Non-monotonic depths
# ---------------------------------------------------------------------------

def test_non_monotonic_depths():
    depths = np.array(
        [0, 10, 5, 20],
        dtype=np.float32,
    )

    temperature = np.array(
        [30, 25, 20, 15],
        dtype=np.float32,
    )

    with pytest.raises(ValueError):
        calculate_thermocline_depth(
            temperature,
            depths,
        )


# ---------------------------------------------------------------------------
# Test 12 — Output metadata
# ---------------------------------------------------------------------------

def test_output_metadata():
    depths = np.array(
        [0, 5, 10, 20],
        dtype=np.float32,
    )

    temperature = xr.DataArray(
        np.array(
            [[30.0, 29.0, 20.0, 19.0]],
            dtype=np.float32,
        ),
        dims=("latitude", "depth"),
        coords={
            "latitude": [10.0],
            "depth": depths,
        },
        name="temperature_mean",
    )

    result = calculate_thermocline(
        temperature,
        depth_dim="depth",
    )

    assert result.name == "thermocline_depth"
    assert result.attrs["units"] == "m"
    assert (
        result.attrs["method"]
        == "maximum absolute vertical temperature gradient"
    )