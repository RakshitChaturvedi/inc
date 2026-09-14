from __future__ import annotations

import copernicusmarine


PRODUCTS = {
    "sst": "SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001",
    "sss": "MULTIOBS_GLO_PHY_S_SURFACE_MYNRT_015_013",
    "ssh": "SEALEVEL_GLO_PHY_L4_NRT_008_046",
    "wind": "WIND_GLO_PHY_L4_NRT_012_004",
    "currents": "MULTIOBS_GLO_PHY_MYNRT_015_003",
}


def inspect_product(
    name: str,
    product_id: str,
) -> None:
    print()
    print("=" * 80)
    print(name.upper())
    print(f"Product ID: {product_id}")
    print("=" * 80)

    catalog = copernicusmarine.describe(
        product_id=product_id,
        disable_progress_bar=True,
    )

    if not catalog.products:
        print("ERROR: product not found")
        return

    product = catalog.products[0]

    print(f"Product title: {product.title}")
    print()

    for dataset in product.datasets:
        print("-" * 80)
        print(f"Dataset ID  : {dataset.dataset_id}")
        print(f"Dataset name: {dataset.dataset_name}")


def main() -> None:
    for name, product_id in PRODUCTS.items():
        try:
            inspect_product(name, product_id)
        except Exception as exc:
            print()
            print(f"{name.upper()} FAILED")
            print(
                f"{type(exc).__name__}: {exc}"
            )


if __name__ == "__main__":
    main()