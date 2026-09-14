from pathlib import Path

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
except ImportError as exc:
    raise SystemExit(
        "\nCartopy is required for the real-coastline overlay.\n"
        "Install it with one of:\n"
        "  conda install -c conda-forge cartopy\n"
        "  pip install cartopy\n"
    ) from exc


MASK_PATH = Path("model-registry/oceanembed-v1.0.0/ocean_mask.nc")
OUTPUT_PATH = Path("data/diagnostics/ocean_mask_vs_real_coast.png")


# Previously identified persistent >3-cell gaps.
PROBLEM_CELLS = [
    (22.25, 72.75),
    (22.75, 70.25),
    (22.75, 90.75),
    (25.00, 50.75),
    (22.00, 72.25),
    (22.25, 72.50),
    (22.25, 72.75),
    (22.50, 69.75),
    (22.75, 70.00),
    (22.75, 70.25),
    (25.00, 50.75),
]


def main():
    if not MASK_PATH.exists():
        raise FileNotFoundError(
            f"Ocean mask not found: {MASK_PATH}"
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with xr.open_dataset(MASK_PATH) as ds:
        mask = ds["ocean_mask"].values.astype(bool)
        lat = ds["latitude"].values
        lon = ds["longitude"].values

    print("=" * 75)
    print("OCEAN MASK vs REAL GEOGRAPHIC COASTLINE")
    print("=" * 75)
    print(f"Mask file       : {MASK_PATH}")
    print(f"Grid shape      : {mask.shape}")
    print(
        f"Latitude        : {lat.min():.2f} -> {lat.max():.2f} °N"
    )
    print(
        f"Longitude       : {lon.min():.2f} -> {lon.max():.2f} °E"
    )
    print(f"Ocean cells     : {mask.sum()}")
    print(f"Land cells      : {(~mask).sum()}")
    print(f"Latitude spacing: {np.median(np.diff(lat)):.2f}°")
    print(f"Longitude spacing: {np.median(np.diff(lon)):.2f}°")

    fig = plt.figure(figsize=(16, 10))

    ax = plt.axes(
        projection=ccrs.PlateCarree()
    )

    ax.set_extent(
        [45, 105, 5, 30],
        crs=ccrs.PlateCarree(),
    )

    # ------------------------------------------------------------------
    # OceanEmbed mask.
    #
    # pcolormesh shows the actual native 0.25° cells rather than
    # smoothing/interpolating the mask.
    # ------------------------------------------------------------------
    ax.pcolormesh(
        lon,
        lat,
        mask.astype(float),
        transform=ccrs.PlateCarree(),
        shading="nearest",
        cmap="Blues",
        vmin=0,
        vmax=1,
        alpha=0.72,
        zorder=1,
    )

    # ------------------------------------------------------------------
    # Real-world geographic features.
    #
    # Cartopy's Natural Earth coastline is independent of the
    # OceanEmbed mask.
    # ------------------------------------------------------------------
    ax.add_feature(
        cfeature.LAND,
        facecolor="white",
        edgecolor="black",
        linewidth=0.5,
        zorder=3,
    )

    ax.add_feature(
        cfeature.COASTLINE,
        edgecolor="black",
        linewidth=1.0,
        zorder=4,
    )

    ax.add_feature(
        cfeature.BORDERS,
        edgecolor="black",
        linewidth=0.45,
        alpha=0.65,
        zorder=4,
    )

    # Rivers are useful for the Bangladesh/Meghna diagnostic,
    # but Cartopy's basic Natural Earth feature may not contain every
    # small river. Treat this as orientation only.
    ax.add_feature(
        cfeature.RIVERS,
        edgecolor="black",
        linewidth=0.35,
        alpha=0.5,
        zorder=4,
    )

    # ------------------------------------------------------------------
    # Geographic latitude/longitude grid.
    #
    # Do this manually rather than using Cartopy Gridliner. This avoids
    # a known Cartopy/Shapely geometry failure during savefig in some
    # version combinations.
    #
    # The mask itself is still plotted on its native 0.25° grid above.
    # These major lines are for geographic orientation.
    # ------------------------------------------------------------------
    for x in np.arange(45, 106, 5):
        ax.plot(
            [x, x],
            [5, 30],
            transform=ccrs.PlateCarree(),
            linewidth=0.35,
            color="gray",
            alpha=0.45,
            linestyle="-",
            zorder=2,
        )

        ax.text(
            x,
            5.15,
            f"{x}°E",
            transform=ccrs.PlateCarree(),
            fontsize=8,
            ha="center",
            va="bottom",
            alpha=0.8,
            zorder=6,
        )

    for y in np.arange(5, 31, 2.5):
        ax.plot(
            [45, 105],
            [y, y],
            transform=ccrs.PlateCarree(),
            linewidth=0.35,
            color="gray",
            alpha=0.45,
            linestyle="-",
            zorder=2,
        )

        ax.text(
            45.2,
            y,
            f"{y:g}°N",
            transform=ccrs.PlateCarree(),
            fontsize=8,
            ha="left",
            va="center",
            alpha=0.8,
            zorder=6,
        )

    # ------------------------------------------------------------------
    # OceanEmbed domain boundary.
    # ------------------------------------------------------------------
    ax.plot(
        [45, 105, 105, 45, 45],
        [5, 5, 30, 30, 5],
        transform=ccrs.PlateCarree(),
        linestyle="--",
        linewidth=1.5,
        color="black",
        label="OceanEmbed domain",
        zorder=5,
    )

    # ------------------------------------------------------------------
    # Problematic cells.
    # ------------------------------------------------------------------
    unique_cells = sorted(set(PROBLEM_CELLS))

    for lat0, lon0 in unique_cells:
        ax.scatter(
            lon0,
            lat0,
            transform=ccrs.PlateCarree(),
            marker="x",
            s=90,
            linewidths=2.2,
            color="red",
            zorder=7,
        )

        ax.annotate(
            f"{lat0:.2f}, {lon0:.2f}",
            xy=(lon0, lat0),
            xycoords=ccrs.PlateCarree()._as_mpl_transform(ax),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=7,
            color="red",
            zorder=8,
        )

    # ------------------------------------------------------------------
    # Labels for the regions relevant to the diagnosis.
    # ------------------------------------------------------------------
    region_labels = [
        (70.0, 27.0, "Gujarat / Kutch"),
        (72.0, 20.0, "Gulf of Khambhat"),
        (90.5, 25.0, "Bangladesh / Meghna"),
        (50.5, 26.5, "Arabian Peninsula"),
        (90.0, 18.0, "Bay of Bengal"),
        (65.0, 18.0, "Arabian Sea"),
    ]

    for x, y, label in region_labels:
        ax.text(
            x,
            y,
            label,
            transform=ccrs.PlateCarree(),
            fontsize=9,
            alpha=0.75,
            ha="center",
            zorder=6,
        )

    ax.set_title(
        "OceanEmbed v1.0.0: Computational Ocean Mask vs Real Coastline\n"
        "Blue = OceanEmbed mask TRUE | Black = geographic coastline | "
        "Red × = persistent unresolved cells",
        fontsize=14,
    )

    ax.legend(
        loc="lower left",
        framealpha=0.9,
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT_PATH,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    print()
    print(f"Saved: {OUTPUT_PATH}")
    print()
    print("Interpretation:")
    print("  Blue ocean-mask cells should broadly overlap geographic ocean.")
    print("  Red X cells can then be classified as:")
    print("    1. genuinely ocean but unsupported by the source product,")
    print("    2. mixed coastal cells, or")
    print("    3. land cells incorrectly marked as ocean.")
    print()
    print("Do NOT modify ocean_mask.nc from this plot alone.")
    print("Use the comparison to decide whether a revised mask is justified.")


if __name__ == "__main__":
    main()
