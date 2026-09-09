from __future__ import annotations

from pathlib import Path

import copernicusmarine


def describe_datasets(product_id: str):
    catalog = copernicusmarine.describe(
        product_id=product_id,
        disable_progress_bar=True,
    )

    if not catalog.products:
        raise RuntimeError(
            f"No Copernicus product found: {product_id}"
        )

    return catalog.products[0].datasets


def resolve_daily_dataset(
    product_id: str,
    preferred_tokens: tuple[str, ...] = (),
) -> str:

    datasets = describe_datasets(product_id)

    candidates = [
        ds.dataset_id
        for ds in datasets
        if "P1D" in ds.dataset_id
        and all(token in ds.dataset_id for token in preferred_tokens)
    ]

    if not candidates:
        raise RuntimeError(
            f"No daily dataset found for {product_id}. "
            f"Candidates: {[d.dataset_id for d in datasets]}"
        )

    preferred = [
        ds
        for ds in candidates
        if "_my_" in ds or "_my" in ds
    ]

    return preferred[0] if preferred else candidates[0]


def resolve_variable(
    dataset_id: str,
    preferred_names: tuple[str, ...],
) -> str:

    catalog = copernicusmarine.describe(
        dataset_id=dataset_id,
        disable_progress_bar=True,
    )

    dataset = catalog.products[0].datasets[0]

    available: list[str] = []

    for version in dataset.versions:
        for part in version.parts:
            for service in part.services:
                available.extend(
                    variable.short_name
                    for variable in service.variables
                )

    available = list(dict.fromkeys(available))

    for name in preferred_names:
        if name in available:
            return name

    raise RuntimeError(
        f"Could not resolve variable for {dataset_id}.\n"
        f"Available variables: {available}"
    )


def acquire_subset(
    *,
    dataset_id: str,
    variables: list[str],
    output_dir: str,
    filename: str,
    start: str,
    end: str,
    bbox: dict,
) -> None:

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    output_path = output / filename

    if output_path.exists():
        print(f"SKIP: {output_path}")
        return

    print(
        "\nDownloading Copernicus dataset\n"
        f"  Dataset   : {dataset_id}\n"
        f"  Variables : {variables}\n"
        f"  Dates     : {start} -> {end}\n"
        f"  Output    : {output_path}"
    )

    copernicusmarine.subset(
        dataset_id=dataset_id,
        variables=variables,

        minimum_longitude=bbox["lon_min"],
        maximum_longitude=bbox["lon_max"],
        minimum_latitude=bbox["lat_min"],
        maximum_latitude=bbox["lat_max"],

        start_datetime=f"{start}T00:00:00",
        end_datetime=f"{end}T23:59:59",

        output_directory=str(output),
        output_filename=filename,

        file_format="netcdf",
        skip_existing=True,
        netcdf_compression_level=4,
    )


def acquire_ssh(cfg: dict) -> None:

    source = cfg["copernicus"]["ssh"]

    if not source.get("enabled", True):
        print("SSH acquisition disabled.")
        return

    dataset_id = resolve_daily_dataset(
        source["product_id"],
        preferred_tokens=("nrt",),
    )

    variable = resolve_variable(
        dataset_id,
        tuple(source["preferred_variables"]),
    )

    acquire_subset(
        dataset_id=dataset_id,
        variables=[variable],
        output_dir=source["output_dir"],
        filename="ssh_2025_2026.nc",
        start=cfg["dates"]["start"],
        end=cfg["dates"]["end"],
        bbox=cfg["domain"],
    )


def acquire_copernicus(cfg: dict) -> None:

    print("\n========================================")
    print("COPERNICUS")
    print("========================================")

    acquire_ssh(cfg)