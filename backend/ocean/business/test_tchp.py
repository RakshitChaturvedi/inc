from __future__ import annotations

import numpy as np
import xarray as xr

from ocean.business.tchp import (
    calculate_tchp,
    calculate_tchp_dataset,
)


DEPTHS = np.array(
    [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000],
    dtype=np.float64,
)


def test_basic_26c_crossing():
    """
    Temperature crosses 26°C between 100 m and 125 m.

    Expected:
        D26 = 112.5 m

    because:
        T(100) = 27°C
        T(125) = 25°C

        26°C is exactly halfway between them.
    """

    temperature = np.array(
        [
            30.0,
            29.5,
            29.0,
            28.5,
            28.0,
            27.5,
            27.0,
            27.0,
            27.0,
            27.0,
            27.0,
            25.0,
            20.0,
            15.0,
            10.0,
        ]
    )

    tchp, d26 = calculate_tchp(
        temperature,
        DEPTHS,
    )

    print("\nTEST 1 — Basic 26°C crossing")
    print(f"D26  : {d26:.3f} m")
    print(f"TCHP : {tchp:.6f} kJ/cm²")

    assert np.isfinite(tchp)
    assert np.isfinite(d26)

    # Crossing is between 200 and 300 m:
    # T(200)=27, T(300)=25 -> D26=250 m
    assert np.isclose(d26, 250.0)


def test_shallow_26c_crossing():
    """
    26°C crossing occurs between 20 m and 30 m.
    """

    temperature = np.array(
        [
            29.0,
            28.0,
            27.0,
            27.0,
            25.0,
            20.0,
            18.0,
            16.0,
            14.0,
            12.0,
            10.0,
            8.0,
            6.0,
            5.0,
            4.0,
        ]
    )

    tchp, d26 = calculate_tchp(
        temperature,
        DEPTHS,
    )

    print("\nTEST 2 — Shallow crossing")
    print(f"D26  : {d26:.3f} m")
    print(f"TCHP : {tchp:.6f} kJ/cm²")

    # T(20)=27, T(30)=25
    # 26°C lies halfway -> 25 m
    assert np.isclose(d26, 25.0)

    assert np.isfinite(tchp)
    assert tchp > 0.0


def test_surface_below_26():
    """
    If SST < 26°C, conventional TCHP should be NaN.
    """

    temperature = np.array(
        [
            25.0,
            24.5,
            24.0,
            23.0,
            22.0,
            21.0,
            20.0,
            19.0,
            18.0,
            17.0,
            16.0,
            15.0,
            14.0,
            13.0,
            12.0,
        ]
    )

    tchp, d26 = calculate_tchp(
        temperature,
        DEPTHS,
    )

    print("\nTEST 3 — Surface below 26°C")
    print(f"D26  : {d26}")
    print(f"TCHP : {tchp}")

    assert np.isnan(tchp)
    assert np.isnan(d26)


def test_entire_column_above_26():
    """
    Entire available water column remains >= 26°C.

    The implementation should integrate to the deepest
    available model level.
    """

    temperature = np.array(
        [
            30.0,
            30.0,
            29.5,
            29.0,
            28.5,
            28.0,
            27.5,
            27.0,
            27.0,
            26.8,
            26.7,
            26.5,
            26.3,
            26.2,
            26.1,
        ]
    )

    tchp, d26 = calculate_tchp(
        temperature,
        DEPTHS,
    )

    print("\nTEST 4 — No 26°C crossing")
    print(f"D26  : {d26:.3f} m")
    print(f"TCHP : {tchp:.6f} kJ/cm²")

    assert np.isfinite(tchp)
    assert np.isfinite(d26)

    assert np.isclose(d26, DEPTHS[-1])


def test_nan_profile():
    """
    A profile with an invalid surface should produce NaN.
    """

    temperature = np.array(
        [
            np.nan,
            29.0,
            28.0,
            27.0,
            26.0,
            25.0,
            24.0,
            23.0,
            22.0,
            21.0,
            20.0,
            19.0,
            18.0,
            17.0,
            16.0,
        ]
    )

    tchp, d26 = calculate_tchp(
        temperature,
        DEPTHS,
    )

    print("\nTEST 5 — Invalid surface")
    print(f"D26  : {d26}")
    print(f"TCHP : {tchp}")

    assert np.isnan(tchp)
    assert np.isnan(d26)


def test_positive_tchp():
    """
    A physically warm column should produce positive heat content.
    """

    temperature = np.array(
        [
            30.0,
            29.5,
            29.0,
            28.5,
            28.0,
            27.5,
            27.0,
            26.5,
            26.2,
            25.8,
            24.0,
            22.0,
            18.0,
            15.0,
            10.0,
        ]
    )

    tchp, d26 = calculate_tchp(
        temperature,
        DEPTHS,
    )

    print("\nTEST 6 — Positive TCHP")
    print(f"D26  : {d26:.3f} m")
    print(f"TCHP : {tchp:.6f} kJ/cm²")

    assert np.isfinite(tchp)
    assert tchp > 0.0
    assert np.isfinite(d26)


def test_multiple_profiles():
    """
    Verify vectorized profile handling.

    Input:
        [profiles, depth]

    Output:
        [profiles]
    """

    temperatures = np.array(
        [
            [
                30.0,
                29.0,
                28.0,
                27.0,
                25.0,
                20.0,
                18.0,
                16.0,
                14.0,
                12.0,
                10.0,
                8.0,
                6.0,
                5.0,
                4.0,
            ],
            [
                28.0,
                27.5,
                27.0,
                26.5,
                25.0,
                23.0,
                20.0,
                18.0,
                16.0,
                14.0,
                12.0,
                10.0,
                8.0,
                6.0,
                4.0,
            ],
        ]
    )

    tchp, d26 = calculate_tchp(
        temperatures,
        DEPTHS,
    )

    print("\nTEST 7 — Multiple profiles")
    print(f"D26  : {d26}")
    print(f"TCHP : {tchp}")

    assert tchp.shape == (2,)
    assert d26.shape == (2,)

    assert np.all(np.isfinite(tchp))
    assert np.all(np.isfinite(d26))


def test_xarray_wrapper():
    """
    Verify the xarray Dataset/DataArray interface used
    by the business layer.
    """

    temperature = np.array(
        [
            [
                30.0,
                29.5,
                29.0,
                28.5,
                28.0,
                27.5,
                27.0,
                26.5,
                26.0,
                25.0,
                23.0,
                20.0,
                17.0,
                14.0,
                10.0,
            ]
        ],
        dtype=np.float32,
    )

    da = xr.DataArray(
        temperature,
        dims=("profile", "depth"),
        coords={
            "profile": [0],
            "depth": DEPTHS,
        },
        name="temperature_mean",
    )

    tchp, d26 = calculate_tchp_dataset(da)

    print("\nTEST 8 — Xarray wrapper")
    print(f"TCHP dimensions : {tchp.dims}")
    print(f"D26 dimensions  : {d26.dims}")
    print(f"TCHP            : {tchp.values}")
    print(f"D26             : {d26.values}")

    assert tchp.dims == ("profile",)
    assert d26.dims == ("profile",)

    assert tchp.shape == (1,)
    assert d26.shape == (1,)

    assert np.isfinite(tchp.values[0])
    assert np.isfinite(d26.values[0])


def test_invalid_depth_dimension():
    """
    Invalid depth dimension should raise ValueError.
    """

    temperature = np.ones((2, 3))

    try:
        calculate_tchp(
            temperature,
            np.array([0.0, 5.0]),
        )
    except ValueError:
        return

    raise AssertionError(
        "Expected ValueError for mismatched depth dimension"
    )


def main():
    """
    Run all tests directly without pytest.
    """

    tests = [
        test_basic_26c_crossing,
        test_shallow_26c_crossing,
        test_surface_below_26,
        test_entire_column_above_26,
        test_nan_profile,
        test_positive_tchp,
        test_multiple_profiles,
        test_xarray_wrapper,
        test_invalid_depth_dimension,
    ]

    print("=" * 70)
    print("OceanEmbed — TCHP Unit Tests")
    print("=" * 70)

    passed = 0

    for test in tests:
        try:
            test()
            print("  PASS")
            passed += 1
        except Exception as exc:
            print(f"  FAIL: {exc}")
            raise

    print("\n" + "=" * 70)
    print(f"RESULT: {passed}/{len(tests)} tests passed")
    print("=" * 70)


if __name__ == "__main__":
    main()