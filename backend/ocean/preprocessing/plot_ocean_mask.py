from pathlib import Path
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

MASK_PATH = Path('model-registry/oceanembed-v1.0.0/ocean_mask.nc')
OUTPUT_PATH = Path('data/diagnostics/ocean_mask_map.png')

PROBLEM_CELLS = {
    'SSS': [(22.25,72.75),(22.75,70.25),(22.75,90.75),(25.00,50.75)],
    'Current U/V': [(22.00,72.25),(22.25,72.50),(22.25,72.75),(22.50,69.75),(22.75,70.00),(22.75,70.25),(25.00,50.75)]
}

def main():
    if not MASK_PATH.exists():
        raise FileNotFoundError(f'Mask not found: {MASK_PATH}')
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with xr.open_dataset(MASK_PATH) as ds:
        if 'ocean_mask' not in ds:
            raise KeyError(f"'ocean_mask' not found: {list(ds.data_vars)}")
        mask = ds['ocean_mask'].values.astype(bool)
        lat = ds['latitude'].values
        lon = ds['longitude'].values

    print('='*70)
    print('OCEAN MASK DIAGNOSTIC')
    print('='*70)
    print(f'File       : {MASK_PATH}')
    print(f'Shape      : {mask.shape}')
    print(f'Latitude   : {lat.min():.2f} -> {lat.max():.2f}')
    print(f'Longitude  : {lon.min():.2f} -> {lon.max():.2f}')
    print(f'Lat step   : {np.median(np.diff(lat)):.2f}°')
    print(f'Lon step   : {np.median(np.diff(lon)):.2f}°')
    print(f'Ocean cells: {mask.sum()}')
    print(f'Land cells : {(~mask).sum()}')

    fig, ax = plt.subplots(figsize=(15,9))
    ax.pcolormesh(lon, lat, mask.astype(float), shading='nearest', cmap='Blues', vmin=0, vmax=1)

    # Native 0.25° grid
    for x in lon: ax.axvline(x, linewidth=0.15, alpha=0.15)
    for y in lat: ax.axhline(y, linewidth=0.15, alpha=0.15)

    unique_cells = sorted(set(c for cells in PROBLEM_CELLS.values() for c in cells))
    for lat0, lon0 in unique_cells:
        ax.scatter(lon0, lat0, marker='x', s=80, linewidths=2)
        ax.annotate(f'{lat0:.2f}, {lon0:.2f}', (lon0,lat0), xytext=(5,5), textcoords='offset points', fontsize=7)

    ax.plot([45,105,105,45,45], [5,5,30,30,5], linestyle='--', linewidth=1.5, label='OceanEmbed domain')
    ax.set(xlim=(45,105), ylim=(5,30), xlabel='Longitude (°E)', ylabel='Latitude (°N)')
    ax.set_title('OceanEmbed v1.0.0 — Native 0.25° Ocean Mask\nBlue = ocean TRUE | White = land FALSE | × = previously unresolved cells')
    ax.set_xticks(np.arange(45,106,5))
    ax.set_yticks(np.arange(5,31,2.5))
    ax.grid(which='major', linewidth=0.5, alpha=0.35)
    ax.legend(loc='lower left')
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, dpi=250, bbox_inches='tight')
    plt.close(fig)
    print(f'\nSaved: {OUTPUT_PATH}')

if __name__ == '__main__':
    main()