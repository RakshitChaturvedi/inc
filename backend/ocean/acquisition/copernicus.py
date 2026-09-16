from __future__ import annotations

from pathlib import Path

import copernicusmarine


def describe_dataset(dataset_id: str):
    """Return the Copernicus dataset object for an explicit dataset ID."""
    catalog = copernicusmarine.describe(
        dataset_id=dataset_id,
        disable_progress_bar=True,
    )

    if not catalog.products:
        raise RuntimeError(
            f"No Copernicus dataset found: {dataset_id}"
        )

    return catalog.products[0].datasets[0]


def resolve_variables(
    dataset_id: str,
    preferred_names: tuple[str, ...],
) -> list[str]:
    """
    Resolve configured variable names against variables exposed
    by the selected Copernicus dataset.
    """
    if not preferred_names:
        raise ValueError(
            f"No preferred variables configured for {dataset_id}"
        )

    dataset = describe_dataset(dataset_id)

    available: list[str] = []

    for version in dataset.versions:
        for part in version.parts:
            for service in part.services:
                for variable in service.variables:
                    if variable.short_name not in available:
                        available.append(variable.short_name)

    missing = [
        name
        for name in preferred_names
        if name not in available
    ]

    if missing:
        raise RuntimeError(
            f"Could not resolve variables for {dataset_id}.\n"
            f"Missing: {missing}\n"
            f"Available: {available}"
        )

    return list(preferred_names)


def acquire_subset(
    *,
    dataset_id: str,
    variables: list[str],
    output_dir: str,
    filename: str,
    start: str,
    end: str,
    bbox: dict[str, float],
) -> Path:
    """Download one spatial/temporal subset from Copernicus Marine."""

    output = Path(output_dir)
    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output / filename

    if output_path.exists():
        print(f"SKIP: {output_path}")
        return output_path

    print(
        "\nDownloading Copernicus dataset\n"
        f"  Dataset   : {dataset_id}\n"
        f"  Variables : {variables}\n"
        f"  Dates     : {start} -> {end}\n"
        f"  Latitude  : {bbox['lat_min']} -> {bbox['lat_max']}\n"
        f"  Longitude : {bbox['lon_min']} -> {bbox['lon_max']}\n"
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

    if not output_path.exists():
        raise RuntimeError(
            "Copernicus subset completed but expected output "
            f"file was not found: {output_path}"
        )

    return output_path


def acquire_variable(
    *,
    source: dict,
    variable: str,
    start: str,
    end: str,
    bbox: dict[str, float],
) -> Path:
    """
    Acquire one logical OceanEmbed variable.

    The source configuration contains an explicit Copernicus
    dataset_id and one or more preferred variables.
    """

    dataset_id = source["dataset_id"]

    preferred_variables = tuple(
        source.get("preferred_variables", ())
    )

    resolved_variables = resolve_variables(
        dataset_id,
        preferred_variables,
    )

    filename = f"{variable}_{start}_{end}.nc"

    return acquire_subset(
        dataset_id=dataset_id,
        variables=resolved_variables,
        output_dir=source["output_dir"],
        filename=filename,
        start=start,
        end=end,
        bbox=bbox,
    )


def acquire_copernicus(cfg: dict) -> None:
    """
    Acquire all enabled Copernicus sources for the configured
    date range and domain.
    """

    sources = cfg["copernicus"]
    bbox = cfg["domain"]

    for variable in (
        "sst",
        "sss",
        "ssh",
        "wind",
        "currents",
    ):
        source = sources[variable]

        if not source.get("enabled", True):
            print(f"Skipping {variable}: disabled")
            continue

        acquire_variable(
            source=source,
            variable=variable,
            start=cfg["dates"]["start"],
            end=cfg["dates"]["end"],
            bbox=bbox,
        )