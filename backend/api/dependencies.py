from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends

from .dataset import OceanDataset, dataset
from .errors import DatasetUnavailableError


def get_dataset() -> Generator[OceanDataset, None, None]:
    if not dataset.dashboard_available:
        raise DatasetUnavailableError(
            "Dashboard dataset is unavailable."
        )

    yield dataset


def get_physics_dataset() -> Generator[OceanDataset, None, None]:
    if not dataset.physics_available:
        raise DatasetUnavailableError(
            "Physics-adjusted dataset is unavailable."
        )

    yield dataset


DatasetDependency = Depends(get_dataset)
PhysicsDatasetDependency = Depends(get_physics_dataset)