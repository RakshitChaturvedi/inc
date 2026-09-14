from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import xarray as xr

from .coverage import CoverageReport
from .models import BoundingBox


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)


def validate_files_exist(
    files: list[Path],
) -> list[str]:
    errors: list[str] = []

    for path in files:
        if not path.exists():
            errors.append(
                f"Acquired file does not exist: {path}"
            )

    return errors


def validate_files_readable(
    files: list[Path],
) -> list[str]:
    errors: list[str] = []

    for path in files:
        if not path.exists():
            continue

        try:
            with xr.open_dataset(path):
                pass
        except Exception as exc:
            errors.append(
                f"Unable to read NetCDF file "
                f"{path}: {exc}"
            )

    return errors


def validate_required_variables(
    files: list[Path],
    required_variables: tuple[str, ...],
) -> list[str]:
    errors: list[str] = []

    if not files:
        errors.append(
            "No acquired files are available."
        )
        return errors

    available_variables: set[str] = set()

    for path in files:
        if not path.exists():
            continue

        try:
            with xr.open_dataset(path) as ds:
                available_variables.update(
                    ds.data_vars
                )
        except Exception:
            continue

    missing = [
        variable
        for variable in required_variables
        if variable not in available_variables
    ]

    for variable in missing:
        errors.append(
            f"Required variable is missing: {variable}"
        )

    return errors


def validate_time_coordinate(
    files: list[Path],
) -> list[str]:
    errors: list[str] = []

    for path in files:
        if not path.exists():
            continue

        try:
            with xr.open_dataset(path) as ds:
                if (
                    "time" not in ds.coords
                    and "time" not in ds.variables
                ):
                    errors.append(
                        f"Missing time coordinate: {path}"
                    )
        except Exception:
            continue

    return errors


def validate_spatial_coordinates(
    files: list[Path],
    region: BoundingBox,
) -> list[str]:
    errors: list[str] = []

    for path in files:
        if not path.exists():
            continue

        try:
            with xr.open_dataset(path) as ds:
                lat_name = _find_coordinate(
                    ds,
                    ("lat", "latitude"),
                )

                lon_name = _find_coordinate(
                    ds,
                    ("lon", "longitude"),
                )

                if lat_name is None:
                    errors.append(
                        f"Missing latitude coordinate: {path}"
                    )
                    continue

                if lon_name is None:
                    errors.append(
                        f"Missing longitude coordinate: {path}"
                    )
                    continue

                lat_values = ds[lat_name].values
                lon_values = ds[lon_name].values

                if len(lat_values) == 0:
                    errors.append(
                        f"Empty latitude coordinate: {path}"
                    )
                    continue

                if len(lon_values) == 0:
                    errors.append(
                        f"Empty longitude coordinate: {path}"
                    )
                    continue

                if (
                    lat_values.max() < region.lat_min
                    or lat_values.min() > region.lat_max
                ):
                    errors.append(
                        f"Latitude coverage does not "
                        f"intersect requested region: {path}"
                    )

                if (
                    lon_values.max() < region.lon_min
                    or lon_values.min() > region.lon_max
                ):
                    errors.append(
                        f"Longitude coverage does not "
                        f"intersect requested region: {path}"
                    )

        except Exception as exc:
            errors.append(
                f"Unable to inspect spatial coordinates "
                f"for {path}: {exc}"
            )

    return errors


def validate_coverage(
    coverage: CoverageReport,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not coverage.has_data:
        errors.append(
            "No temporal coverage is available."
        )
        return errors, warnings

    if not coverage.is_complete:
        warnings.append(
            "Requested temporal coverage is incomplete."
        )

    return errors, warnings


def _find_coordinate(
    ds: xr.Dataset,
    candidates: tuple[str, ...],
) -> str | None:
    for name in candidates:
        if name in ds.coords or name in ds.variables:
            return name

    return None


def validate_acquisition(
    *,
    files: list[Path],
    required_variables: tuple[str, ...],
    region: BoundingBox,
    coverage: CoverageReport,
) -> ValidationResult:
    """
    Validate acquired files against the acquisition contract.

    This validates acquisition artifacts only. It does not perform
    scientific preprocessing, normalization, regridding, or inference.
    """

    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(
        validate_files_exist(files)
    )

    errors.extend(
        validate_files_readable(files)
    )

    errors.extend(
        validate_required_variables(
            files,
            required_variables,
        )
    )

    errors.extend(
        validate_time_coordinate(files)
    )

    errors.extend(
        validate_spatial_coordinates(
            files,
            region,
        )
    )

    coverage_errors, coverage_warnings = (
        validate_coverage(coverage)
    )

    errors.extend(coverage_errors)
    warnings.extend(coverage_warnings)

    return ValidationResult(
        valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )