from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from functools import cached_property
from typing import Any, Callable, Self

import dask.array
import dask.dataframe as dd
import numpy as np
import pandas as pd
import xarray as xr

from lib.dimension import Dimension


@dataclass(kw_only=True, frozen=True)
class Metadata:
    var_name: str | None = None
    display_latex: str | None = None
    unit_latex: str = ""
    name_fragments: list[str] = field(default_factory=list)

    spatial_dims: list[str] = field(default_factory=list)
    time_dim: str | None = None
    color_dim: str | None = None

    dims: dict[str, Dimension] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def keys(self) -> tuple[str, ...]:
        # along with __getitem__, enables ** unpacking
        return (f.name for f in fields(self))

    @classmethod
    def create_from(cls, other: Metadata, /, **extra_vals: Any) -> Self:
        """
        Transmutes an instance of some other `Metadata` type to one of this class.
        It's ok for `other` to have keys not present in this class—they are silently ignored—but invalid keys in `extra_vals` cause an exception.

        Also note that `extra_vals` a) takes precedence over values in `other`, and b) must provide any missing values required by this class that `other` lacks.
        """
        my_keys = {f.name for f in fields(cls)}
        mutual_keys = my_keys & set(other.keys())
        vals_from_other = {key: other[key] for key in mutual_keys}
        vals = vals_from_other | extra_vals

        return cls(**vals)

    def assign(self, **vals: Any) -> Self:
        """Returns a copy of this metadata with new values assigned. Invalid keys cause an exception."""
        updated_vals = {**self} | vals
        return self.__class__(**updated_vals)


@dataclass(frozen=True, init=False)
class DataWithAttrs[D: xr.DataArray | pd.DataFrame | dd.DataFrame, MD: Metadata](ABC):
    """A data wrapper to provide a uniform, typed, and reliable metadata interface."""

    # The type checker ignores type bounds when no generic argument is present, e.g. after `isinstance` (and function parameters).
    # Specifying field data types like this makes their types known in such cases, but doesn't give type hints for the parameters of __init__.
    # Thus, it's necessary to annotate __init__ parameters via generics and the fields themselves with concrete types.
    # Unfortunately, annotating a field in a superclass requires also annotating it in each subclass that refines that field's type.
    # And with all this, other methods still don't get type hints :(
    data: xr.DataArray | pd.DataFrame | dd.DataFrame
    metadata: Metadata
    _caches: dict[str, dict[str, Any]]

    def __init__(self, data: D, metadata: MD):
        object.__setattr__(self, "data", data)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "_caches", {})

    @property
    @abstractmethod
    def coordss(self) -> dict[str, np.ndarray]: ...

    @property
    @abstractmethod
    def dims(self) -> list[str]: ...

    def assign_data(self, data: D) -> Self:
        return self.__class__(data, self.metadata)

    def assign_metadata(self, metadata: MD | None = None, /, **metadata_vals: Any) -> Self:
        if not (metadata or metadata_vals):
            return self
        return self.__class__(self.data, (metadata or self.metadata).assign(**metadata_vals))

    def assign(self, data: D, metadata: MD | None = None, /, **metadata_vals: Any) -> Self:
        return self.assign_data(data).assign_metadata(metadata, **metadata_vals)

    def map_data(self, func: Callable[[D], D]) -> Self:
        return self.assign_data(func(self.data))

    @abstractmethod
    def bounds(self, dim_name: str) -> tuple[float, float]: ...

    @abstractmethod
    def lower_bound(self, dim_name: str) -> float: ...

    @abstractmethod
    def upper_bound(self, dim_name: str) -> float: ...


@dataclass(kw_only=True, frozen=True)
class FieldMetadata(Metadata):
    prefix: str | None = None


class Field(DataWithAttrs[xr.Dataset, FieldMetadata]):
    data: xr.Dataset
    metadata: FieldMetadata

    @property
    def active_data(self) -> xr.DataArray:
        if self.metadata.var_name is None:
            raise ValueError("no active variable; specify one as a positional argument")
        return self.data[self.metadata.var_name]

    def with_active_data(self, new_da: xr.DataArray) -> Self:
        """Returns a copy with the active variable replaced by `new_da`. Sibling variables that
        are no longer compatible with the new active grid (e.g. share a dim name with different
        coordinate values) are dropped."""
        var_name = self.metadata.var_name
        new_ds = new_da.to_dataset(name=var_name)
        for sib in self.data.data_vars:
            if sib == var_name:
                continue
            try:
                new_ds = xr.merge([new_ds, self.data[[sib]]], join="exact", compat="no_conflicts")
            except (xr.MergeError, ValueError):
                pass
        return self.assign_data(new_ds)

    @cached_property
    def coordss(self) -> dict[str, np.ndarray]:
        active = self.active_data
        return {dim: np.array(active.coords[dim]) for dim in active.coords.keys()}

    @cached_property
    def dims(self) -> list[str]:
        return list(self.active_data.dims)

    def bounds(self, dim_name):
        return (self.lower_bound(dim_name), self.upper_bound(dim_name))

    def lower_bound(self, dim_name) -> float:
        return self.coordss[dim_name][0]

    def upper_bound(self, dim_name) -> float:
        coords = self.coordss[dim_name]
        delta = coords[1] - coords[0]
        return coords[-1] + delta

    @cached_property
    def var_bounds(self) -> tuple[float, float]:
        active = self.active_data
        return dask.compute(np.min(active), np.max(active))


@dataclass(kw_only=True, frozen=True)
class ListMetadata(Metadata):
    coordss: dict[str, np.ndarray] = field(default_factory=dict)
    dependent_var: str | None = None
    weight_var: str | None = None


class List[D: pd.DataFrame | dd.DataFrame](DataWithAttrs[D, ListMetadata]):
    data: pd.DataFrame | dd.DataFrame
    metadata: ListMetadata

    @property
    def active_data(self) -> pd.Series | dd.Series:
        if self.metadata.var_name is None:
            raise ValueError("no active variable; specify one as a positional argument")
        return self.data[self.metadata.var_name]

    def with_active_data(self, series: pd.Series | dd.Series) -> Self:
        return self.assign_data(self.data.assign(**{self.metadata.var_name: series}))

    @abstractmethod
    def compute(self) -> FullList: ...

    @property
    def coordss(self) -> dict[str, np.ndarray]:
        return self.metadata.coordss

    @property
    def dims(self) -> list[str]:
        return list(self.data.columns)


class FullList(List[pd.DataFrame]):
    data: pd.DataFrame

    def compute(self) -> FullList:
        return self

    def bounds(self, dim_name):
        return (self.lower_bound(dim_name), self.upper_bound(dim_name))

    def lower_bound(self, dim_name) -> float:
        cache = self._caches.setdefault("lower_bound", {})
        if dim_name not in cache:
            if dim_name in self.coordss:
                cache[dim_name] = self.coordss[dim_name][0]
            else:
                cache[dim_name] = self.data[dim_name].min(skipna=True)
        return cache[dim_name]

    def upper_bound(self, dim_name) -> float:
        cache = self._caches.setdefault("upper_bound", {})
        if dim_name not in cache:
            if dim_name in self.coordss:
                coords = self.coordss[dim_name]
                delta = coords[1] - coords[0]
                cache[dim_name] = coords[-1] + delta
            else:
                cache[dim_name] = self.data[dim_name].max(skipna=True)
        return cache[dim_name]


class LazyList(List[dd.DataFrame]):
    data: dd.DataFrame

    def compute(self) -> FullList:
        return FullList(self.data.compute(), self.metadata)

    def bounds(self, dim_name):
        cache = self._caches.setdefault("bounds", {})
        if dim_name not in cache:
            if dim_name in self.coordss:
                coords = self.coordss[dim_name]
                lower = coords[0]
                delta = coords[1] - coords[0]
                upper = coords[-1] + delta
                cache[dim_name] = (lower, upper)
            else:
                cache[dim_name] = dask.array.compute(self.data[dim_name].min(skipna=True), self.data[dim_name].max(skipna=True))
        return cache[dim_name]

    def lower_bound(self, dim_name) -> float:
        return self.bounds(dim_name)[0]

    def upper_bound(self, dim_name) -> float:
        return self.bounds(dim_name)[1]
