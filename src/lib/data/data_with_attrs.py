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

from lib.file_util import Prepath
from lib.latex import Latex
from lib.species import SpeciesInfo
from lib.var_info import VarInfo


@dataclass(kw_only=True, frozen=True)
class Metadata:
    active_key: str | None = None

    var_infos: dict[str, VarInfo] = field(default_factory=dict)
    species: dict[str, SpeciesInfo] = field(default_factory=dict)

    @property
    def active_var_info(self) -> VarInfo:
        if self.active_key is None:
            raise ValueError("no active variable; specify one as a positional argument")
        return self.var_infos[self.active_key]

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


@dataclass(frozen=True)
class DataWithAttrs[Data, Subdata, MD: Metadata = Metadata](ABC):
    """A data wrapper to provide a uniform, typed, and reliable metadata interface."""

    data: Data
    metadata: MD
    _caches: dict[str, dict[str, Any]] = field(default_factory=dict, init=False)

    @property
    @abstractmethod
    def coordss(self) -> dict[str, np.ndarray]: ...

    @property
    @abstractmethod
    def dims(self) -> list[str]: ...

    @property
    def active_key(self) -> str | None:
        return self.metadata.active_key

    @property
    def active_subdata(self) -> Subdata | None:
        if self.active_key is None:
            return None
        return self[self.active_key]

    @property
    def active_info(self) -> VarInfo | None:
        if self.active_key is None:
            return None
        return self.metadata.var_infos[self.active_key]

    @abstractmethod
    def __getitem__(self, key: str) -> Subdata: ...

    @abstractmethod
    def with_active(self, *, data: Subdata | None = None, key: str | None = None, info: VarInfo | None = None) -> Self: ...

    def with_info(self, key: str, info: VarInfo) -> Self:
        return self.assign_metadata(var_infos=self.metadata.var_infos | {key: info})

    def assign_data(self, data: Data) -> Self:
        return self.__class__(data, self.metadata)

    def assign_metadata(self, metadata: MD | None = None, /, **metadata_vals: Any) -> Self:
        if not (metadata or metadata_vals):
            return self
        return self.__class__(self.data, (metadata or self.metadata).assign(**metadata_vals))

    def assign(self, data: Data, metadata: MD | None = None, /, **metadata_vals: Any) -> Self:
        return self.assign_data(data).assign_metadata(metadata, **metadata_vals)

    @abstractmethod
    def bounds(self, dim_name: str) -> tuple[float, float]: ...

    @abstractmethod
    def lower_bound(self, dim_name: str) -> float: ...

    @abstractmethod
    def upper_bound(self, dim_name: str) -> float: ...

    @abstractmethod
    def dask_collections(self) -> list: ...


@dataclass(kw_only=True, frozen=True)
class FieldMetadata(Metadata):
    prepath: Prepath | None = None


class Field(DataWithAttrs[dict[str, xr.DataArray], xr.DataArray, FieldMetadata]):
    @property
    def active_data(self) -> xr.DataArray:
        if self.metadata.active_key is None:
            raise ValueError("no active variable; specify one as a positional argument")
        return self.data[self.metadata.active_key]

    def with_active(self, *, data=None, key=None, info=None) -> Self:
        if data is None and info is None:
            return self.assign_metadata(active_key=key)

        key = key or self.metadata.active_key
        assert key is not None

        ret = self
        if data is not None:
            ret = ret.assign(ret.data | {key: data}, active_key=key)

        if info is not None:
            ret = ret.assign_metadata(var_infos=ret.metadata.var_infos | {key: info}, active_key=key)

        return ret

    def __getitem__(self, key: str):
        return self.data[key]

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

    def dask_collections(self) -> list:
        return [da.data for da in self.data.values() if dask.is_dask_collection(da.data)]


@dataclass(kw_only=True, frozen=True)
class ListMetadata(Metadata):
    coordss: dict[str, np.ndarray] = field(default_factory=dict)
    weight_key: str | None = None

    subject: Latex | None = None
    """The `subject` is essentially the (display) name of the list's implicit index dimension."""

    partition_dim: str | None = None
    """If set, the dim along which partitions of `data` are laid out. Each
    value of this dim corresponds to a contiguous range of partitions given
    by `partition_ranges`. Used by `Idx` to do dask-native partition pruning
    instead of a predicate filter."""

    partition_ranges: list[tuple[int, int]] | None = None
    """Per-value `(start, end)` partition index ranges along `partition_dim`.
    `len(partition_ranges) == len(coordss[partition_dim])`."""


class List[Data: pd.DataFrame | dd.DataFrame = pd.DataFrame | dd.DataFrame, Subdata: pd.Series | dd.Series = pd.Series | dd.Series](DataWithAttrs[Data, Subdata, ListMetadata]):
    @property
    def active_data(self) -> pd.Series | dd.Series:
        if self.metadata.active_key is None:
            raise ValueError("no active variable; specify one as a positional argument")
        return self.data[self.metadata.active_key]

    def with_active(self, *, data=None, key=None, info=None) -> Self:
        if data is None and info is None:
            return self.assign_metadata(active_key=key)

        key = key or self.metadata.active_key
        assert key is not None

        ret = self
        if data is not None:
            ret = ret.assign(ret.data.assign(**{key: data}), active_key=key)

        if info is not None:
            ret = ret.assign_metadata(var_infos=ret.metadata.var_infos | {key: info}, active_key=key)

        return ret

    @abstractmethod
    def compute(self) -> FullList: ...

    @property
    def coordss(self) -> dict[str, np.ndarray]:
        return self.metadata.coordss

    @property
    def dims(self) -> list[str]:
        return list(self.data.columns)


class FullList(List[pd.DataFrame]):
    def __getitem__(self, key: str):
        return self.data[key]

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

    def dask_collections(self) -> list:
        return []


class LazyList(List[dd.DataFrame]):
    def __getitem__(self, key: str):
        return self.data[key]

    def compute(self) -> FullList:
        # partition_* describe the dask layout; meaningless after compute.
        return FullList(self.data.compute(), self.metadata.assign(partition_dim=None, partition_ranges=None))

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

    def dask_collections(self) -> list:
        return [self.data]
