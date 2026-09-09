from __future__ import annotations

import numpy as np
import xarray as xr

from ocean.business.mld import (
    calculate_mld,
    calculate_mld_dataset,
)


DEPTHS = np.array(
    [
        0,
        5,
        10,
        20,
        30,
        50,
        75,
        100,
        125,
        150,
        200,
        300,
        500,
        700,
        1000,
    ],
    dtype=np.float32,
)


def test_basic_mld():
    """
    Density remains within threshold through 30 m and exceeds
    the threshold at 50 m.

    Expected MLD = 30 m or an interpolated value between 30 and 50 m.
    """

    temperature = np.array(
        [
            29.0,
            28.9,
            28.8,
            28.7,
            28.0,
            25.0,
            22.0,
            20.0,
            18.0,
            16.0,
            14.0,
            12.0,
            10.0,
            8.0,
            6.0,
        ],
        dtype=np.float32,
    )

    salinity = np.array(
        [
            35.0,
            35.0,
            35.0,
            35.0,
            35.0,
            35.0,
            35.0,
            35.0,
            35.0,
            35.0,
            35.0,
            35.0,
            35.0,
            35.0,
            35.0,
        ],
        dtype=np.float32,
    )

    mld = calculate_mld(
        temperature,
        salinity,
        DEPTHS,
    )

    print("\nTEST 1 — Basic MLD")
    print(f"MLD: {mld:.3f} m")

    assert np.isfinite(mld)
    assert mld >= 10.0
    assert mld <= 50.0


def test_shallow_mixed_layer():
    """
    Strong density change occurs immediately below 10 m.
    """

    temperature = np.array(
        [
            29.0,
            29.0,
            29.0,
            20.0,
            18.0,
            16.0,
            14.0,
            12.0,
            10.0,
            9.0,
            8.0,
            7.0,
            6.0,
            5.0,
            4.0,
        ],
        dtype=np.float32,
    )

    salinity = np.full(
        len(DEPTHS),
        35.0,
        dtype=np.float32,
    )

    mld = calculate_mld(
        temperature,
        salinity,
        DEPTHS,
    )

    print("\nTEST 2 — Shallow MLD")
    print(f"MLD: {mld:.3f} m")

    assert np.isfinite(mld)
    assert mld >= 10.0
    assert mld <= 20.0


def test_deep_mixed_layer():
    """
    Nearly uniform warm/saline column.

    The entire available column should remain inside
    the density threshold.
    """

    temperature = np.full(
        len(DEPTHS),
        28.0,
        dtype=np.float32,
    )

    salinity = np.full(
        len(DEPTHS),
        35.0,
        dtype=np.float32,
    )

    mld = calculate_mld(
        temperature,
        salinity,
        DEPTHS,
    )

    print("\nTEST 3 — Deep mixed layer")
    print(f"MLD: {mld:.3f} m")

    assert np.isfinite(mld)
    assert np.isclose(mld, DEPTHS[-1])


def test_salinity_driven_stratification():
    """
    Temperature remains constant while salinity increases
    strongly with depth.

    This verifies that MLD actually uses density rather than
    being temperature-only.
    """

    temperature = np.full(
        len(DEPTHS),
        28.0,
        dtype=np.float32,
    )

    salinity = np.array(
        [
            35.0,
            35.0,
            35.0,
            35.0,
            36.0,
            36.5,
            37.0,
            37.5,
            38.0,
            38.5,
            39.0,
            40.0,
            41.0,
            42.0,
            43.0,
        ],
        dtype=np.float32,
    )

    mld = calculate_mld(
        temperature,
        salinity,
        DEPTHS,
    )

    print("\nTEST 4 — Salinity-driven stratification")
    print(f"MLD: {mld:.3f} m")

    assert np.isfinite(mld)
    assert mld < DEPTHS[-1]


def test_nan_profile():
    """
    Invalid reference-level data should produce NaN.
    """

    temperature = np.array(
        [
            29.0,
            28.5,
            np.nan,
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
        ],
        dtype=np.float32,
    )

    salinity = np.full(
        len(DEPTHS),
        35.0,
        dtype=np.float32,
    )

    mld = calculate_mld(
        temperature,
        salinity,
        DEPTHS,
    )

    print("\nTEST 5 — Invalid reference level")
    print(f"MLD: {mld}")

    assert np.isnan(mld)


def test_multiple_profiles():
    """
    Verify multiple vertical profiles.
    """

    temperatures = np.array(
        [
            [
                29.0,
                28.9,
                28.8,
                28.7,
                28.0,
                25.0,
                22.0,
                20.0,
                18.0,
                16.0,
                14.0,
                12.0,
                10.0,
                8.0,
                6.0,
            ],
            [
                28.0,
                28.0,
                28.0,
                28.0,
                28.0,
                28.0,
                28.0,
                28.0,
                28.0,
                28.0,
                28.0,
                28.0,
                28.0,
                28.0,
                28.0,
            ],
        ],
        dtype=np.float32,
    )

    salinities = np.full_like(
        temperatures,
        35.0,
    )

    mld = calculate_mld(
        temperatures,
        salinities,
        DEPTHS,
    )

    print("\nTEST 6 — Multiple profiles")
    print(f"MLD: {mld}")

    assert mld.shape == (2,)
    assert np.all(np.isfinite(mld))

    assert mld[0] < mld[1]


def test_xarray_wrapper():
    """
    Verify the xarray interface.
    """

    temperature = xr.DataArray(
        np.array(
            [
                [
                    29.0,
                    28.9,
                    28.8,
                    28.7,
                    28.0,
                    25.0,
                    22.0,
                    20.0,
                    18.0,
                    16.0,
                    14.0,
                    12.0,
                    10.0,
                    8.0,
                    6.0,
                ]
            ],
            dtype=np.float32,
        ),
        dims=("profile", "depth"),
        coords={
            "profile": [0],
            "depth": DEPTHS,
        },
        name="temperature_mean",
    )

    salinity = xr.DataArray(
        np.full(
            (1, len(DEPTHS)),
            35.0,
            dtype=np.float32,
        ),
        dims=("profile", "depth"),
        coords={
            "profile": [0],
            "depth": DEPTHS,
        },
        name="salinity_mean",
    )

    mld = calculate_mld_dataset(
        temperature,
        salinity,
    )

    print("\nTEST 7 — Xarray wrapper")
    print(f"Dimensions: {mld.dims}")
    print(f"Values: {mld.values}")

    assert mld.dims == ("profile",)
    assert mld.shape == (1,)
    assert np.isfinite(mld.values[0])


def test_mismatched_shapes():
    """
    Temperature and salinity must have identical shapes.
    """

    temperature = np.ones(
        len(DEPTHS),
        dtype=np.float32,
    )

    salinity = np.ones(
        len(DEPTHS) - 1,
        dtype=np.float32,
    )

    try:
        calculate_mld(
            temperature,
            salinity,
            DEPTHS,
        )
    except ValueError:
        return

    raise AssertionError(
        "Expected ValueError for mismatched shapes"
    )


def test_invalid_depths():
    """
    Depths must be strictly increasing.
    """

    temperature = np.ones(
        len(DEPTHS),
        dtype=np.float32,
    )

    salinity = np.ones(
        len(DEPTHS),
        dtype=np.float32,
    )

    bad_depths = DEPTHS.copy()
    bad_depths[5] = bad_depths[4]

    try:
        calculate_mld(
            temperature,
            salinity,
            bad_depths,
        )
    except ValueError:
        return

    raise AssertionError(
        "Expected ValueError for non-monotonic depths"
    )


def main():
    tests = [
        test_basic_mld,
        test_shallow_mixed_layer,
        test_deep_mixed_layer,
        test_salinity_driven_stratification,
        test_nan_profile,
        test_multiple_profiles,
        test_xarray_wrapper,
        test_mismatched_shapes,
        test_invalid_depths,
    ]

    print("=" * 70)
    print("OceanEmbed — MLD Unit Tests")
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