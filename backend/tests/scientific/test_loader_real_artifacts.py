from pathlib import Path
from ocean.scientific.data.loader import ScientificDataset

PHYSICS_PATH = Path("data/physics/physics_adjusted.nc")
MASK_PATH = Path("model-registry/oceanembed-v1.0.0/ocean_mask_3d.nc")

def main() -> None:
    print("=" * 60)
    print("OceanEmbed ScientificDataset — Real Artifact Test")
    print("=" * 60)

    print(f"Physics: {PHYSICS_PATH}")
    print(f"Mask:    {MASK_PATH}")
    print()

    with ScientificDataset(
        physics_path=PHYSICS_PATH,
        mask_path=MASK_PATH,
        validate=True,
    ) as state:

        print("VALIDATION: PASS")
        print()

        print("TEMPERATURE")
        print(f"  dims:  {state.temperature.dims}")
        print(f"  shape: {state.temperature.shape}")
        print()

        print("SALINITY")
        print(f"  dims:  {state.salinity.dims}")
        print(f"  shape: {state.salinity.shape}")
        print()

        print("COORDINATES")
        print(f"  time:      {state.time.shape}")
        print(f"  depth:     {state.depth.values}")
        print(f"  latitude:  {state.latitude.shape}")
        print(f"  longitude: {state.longitude.shape}")
        print()

        print("3D MASK")
        print(f"  dims:  {state.ocean_mask_3d.dims}")
        print(f"  shape: {state.ocean_mask_3d.shape}")
        print()

        print("SOURCE")
        for name, path in state.source_paths.items():
            print(f"  {name}: {path}")

    print()
    print("ScientificDataset real-artifact validation complete.")


if __name__ == "__main__":
    main()