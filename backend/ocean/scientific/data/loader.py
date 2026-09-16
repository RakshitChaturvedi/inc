from pathlib import Path

import xarray as xr

from .schema import ScientificSchema
from .coordinates import (
    validate_regular_grid,
    validate_domain,
    validate_depths,
)
from .masks import validate_mask_shape, validate_mask_coordinates


class ScientificDataset:
    """
    Canonical scientific-state interface for OceanEmbed.

    Provides validated temperature/salinity fields,
    coordinates, and the depth-aware ocean mask.
    """

    def __init__(
        self,
        physics_path: str | Path,
        mask_path: str | Path,
        *,
        schema: ScientificSchema | None = None,
        validate: bool = True,
    ):
        self.schema = schema or ScientificSchema()

        self.physics_path = Path(physics_path)
        self.mask_path = Path(mask_path)

        if not self.physics_path.exists():
            raise FileNotFoundError(
                f"Physics artifact not found: {self.physics_path}"
            )

        if not self.mask_path.exists():
            raise FileNotFoundError(
                f"3D mask artifact not found: {self.mask_path}"
            )

        self._dataset = xr.open_dataset(
            self.physics_path
        )

        self._mask_dataset = xr.open_dataset(
            self.mask_path
        )

        if validate:
            self.validate()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def close(self) -> None:
        self._dataset.close()
        self._mask_dataset.close()
    
    @property
    def temperature(self) -> xr.DataArray:
        return self._dataset[self.schema.temperature_name]

    @property
    def salinity(self) -> xr.DataArray:
        return self._dataset[self.schema.salinity_name]

    @property
    def temperature_std(self) -> xr.DataArray:
        return self._dataset[self.schema.temperature_std_name]

    @property
    def salinity_std(self) -> xr.DataArray:
        return self._dataset[self.schema.salinity_std_name]

    @property
    def time(self):
        return self._dataset[self.schema.time_dim]

    @property
    def depth(self):
        return self._dataset[self.schema.depth_dim]

    @property
    def latitude(self):
        return self._dataset[self.schema.latitude_dim]

    @property
    def longitude(self):
        return self._dataset[self.schema.longitude_dim]

    @property
    def ocean_mask_3d(self) -> xr.DataArray:
        if "ocean_mask_3d" in self._mask_dataset.data_vars:
            mask = self._mask_dataset["ocean_mask_3d"]
        elif "__xarray_dataarray_variable__" in self._mask_dataset.data_vars:
            mask = self._mask_dataset["__xarray_dataarray_variable__"]
        else:
            raise ValueError(f"3D ocean mask variable not found. Available variables {list(self._mask_dataset.data_vars)}")

        return mask

    @property
    def masked_temperature(self) -> xr.DataArray:
        return self.temperature.where(self.ocean_mask_3d)

    @property
    def masked_salinity(self) -> xr.DataArray:
        return self.salinity.where(self.ocean_mask_3d)

    @property
    def source_paths(self) -> dict[str,  str]:
        return {
            "physics": str(self.physics_path),
            "mask": str(self.mask_path)
        }

    @property
    def attrs(self):
        return self._dataset.attrs

    def validate(self) -> None:
        self._validate_variables()
        self._validate_dimensions()
        self._validate_coordinates()
        self._validate_mask()


    def _validate_dimensions(self) -> None:
        required_dims = {
            self.schema.time_dim,
            self.schema.depth_dim,
            self.schema.latitude_dim,
            self.schema.longitude_dim
        }
        missing = required_dims - set(self._dataset.dims)
        if missing:
            raise ValueError(f"Missing dimensions: {sorted(missing)}")

    def _validate_coordinates(self) -> None:
        validate_regular_grid(self.latitude.values, self.longitude.values, resolution=self.schema.resolution_deg)
        validate_domain(
            self.latitude.values, self.longitude.values,
            lat_min=self.schema.lat_min, lat_max=self.schema.lat_max,
            lon_min=self.schema.lon_min, lon_max=self.schema.lon_max,
        )
        validate_depths(self.depth.values, self.schema.expected_depths_m)

    def _validate_mask(self) -> None:
        mask = self.ocean_mask_3d
        validate_mask_shape(mask,self.temperature)
        validate_mask_coordinates(mask,self.temperature)

    def _validate_variables(self) -> None:
        required = {
            self.schema.temperature_name,
            self.schema.salinity_name,
            self.schema.temperature_std_name,
            self.schema.salinity_std_name,
        }

        missing = required - set(self._dataset.data_vars)

        if missing:
            raise ValueError(
                f"Missing scientific variables: {sorted(missing)}"
            )

        expected_dims = (
            self.schema.time_dim,
            self.schema.depth_dim,
            self.schema.latitude_dim,
            self.schema.longitude_dim,
        )

        for variable_name in required:
            variable = self._dataset[variable_name]

            if variable.dims != expected_dims:
                raise ValueError(
                    f"{variable_name} has unexpected dimensions: "
                    f"expected {expected_dims}, "
                    f"got {variable.dims}."
                )