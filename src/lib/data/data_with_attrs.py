from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from functools import cached_property
from typing import Any, Self

import dask
import dask.dataframe as dd
import numpy as np
import pandas as pd
import xarray as xr

from lib.data.types import Bounds, Coords, DimKey, SpeciesKey, SubdataKey, VarKey
from lib.file_util import Prepath
from lib.latex import Latex
from lib.species import SpeciesInfo
from lib.var_info import VarInfo


@dataclass(kw_only=True, frozen=True)
class Metadata:
    prepath: Prepath
    active_key: SubdataKey | None = None

    var_infos: dict[VarKey, VarInfo] = field(default_factory=dict)
    species: dict[SpeciesKey, SpeciesInfo] = field(default_factory=dict)

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
    def dims(self) -> list[VarKey]: ...

    @property
    def active_key(self) -> SubdataKey | None:
        return self.metadata.active_key

    @property
    def active_subdata(self) -> Subdata | None:
        if self.active_key is None:
            return None
        return self[self.active_key]

    def require_active_key(self) -> SubdataKey:
        if self.active_key is None:
            raise ValueError("No active variable.")
        return self.active_key

    def require_active_subdata(self) -> Subdata:
        return self[self.require_active_key()]

    @property
    def active_info(self) -> VarInfo | None:
        if self.active_key is None:
            return None
        return self.metadata.var_infos[self.active_key]

    def __getitem__(self, key) -> dd.Series:
        return self.data[key]

    @abstractmethod
    def with_active(self, *, data: Subdata | None = None, key: SubdataKey | None = None, info: VarInfo | None = None) -> Self: ...

    def with_info(self, key: VarKey, info: VarInfo) -> Self:
        return self.assign(var_infos=self.metadata.var_infos | {key: info})

    def assign(self, data: Data | None = None, /, **metadata_vals: Any) -> Self:
        return self.__class__(self.data if data is None else data, self.metadata.assign(**metadata_vals))

    @abstractmethod
    def bounds(self, key: VarKey) -> Bounds:
        """Determine the lower and upper bounds for the given variable. A variable's coordinates, if present, are prioritized over the data itself."""

    @abstractmethod
    def coordss(self, key: SubdataKey | None = None) -> dict[DimKey, Coords]: ...

    @abstractmethod
    def dask_collections(self) -> list: ...


class FieldMetadata(Metadata): ...


class Field(DataWithAttrs[dict[str, xr.DataArray], xr.DataArray, FieldMetadata]):
    def with_active(self, *, data=None, key=None, info=None) -> Self:
        if data is None and info is None:
            return self.assign(active_key=key)

        key = key or self.metadata.active_key
        assert key is not None

        ret = self
        if data is not None:
            ret = ret.assign(ret.data | {key: data}, active_key=key)

        if info is not None:
            ret = ret.assign(var_infos=ret.metadata.var_infos | {key: info}, active_key=key)

        return ret

    def coordss(self, key: SubdataKey | None = None) -> dict[DimKey, Coords]:
        subdata = self[key or self.active_key]
        return {dim: np.array(subdata.coords[dim]) for dim in subdata.coords.keys()}

    @cached_property
    def dims(self) -> list[str]:
        return list(self.require_active_subdata().dims)

    def bounds(self, key: VarKey) -> Bounds:
        if (active := self.active_subdata) is not None and key in active.coords:
            coords = active.coords[key]
            delta = coords[1] - coords[0]
            return coords[0], coords[-1] + delta
        elif key in self.data:
            subdata = self[key]
            lower, upper = dask.compute(subdata.min(skipna=True), subdata.max(skipna=True), traverse=False)
            return lower[()], upper[()]
        else:
            raise RuntimeError(f"unknown key {key}")

    def dask_collections(self) -> list:
        return [da.data for da in self.data.values() if dask.is_dask_collection(da.data)]


@dataclass(kw_only=True, frozen=True)
class ListMetadata(Metadata):
    coordss: dict[DimKey, np.ndarray] = field(default_factory=dict)
    weight_key: SubdataKey | None = None

    subject: Latex | None = None
    """The `subject` is essentially the (display) name of the list's implicit index dimension."""

    partition_dim: SubdataKey | None = None
    """If set, the dim along which partitions of `data` are laid out. Each
    value of this dim corresponds to a contiguous range of partitions given
    by `partition_ranges`. Used by `Idx` to do dask-native partition pruning
    instead of a predicate filter."""

    partition_ranges: list[tuple[int, int]] | None = None
    """Per-value `(start, end)` partition index ranges along `partition_dim`.
    `len(partition_ranges) == len(coordss[partition_dim])`."""


class List[Data: pd.DataFrame | dd.DataFrame = pd.DataFrame | dd.DataFrame, Subdata: pd.Series | dd.Series = pd.Series | dd.Series](DataWithAttrs[Data, Subdata, ListMetadata]):
    def with_active(self, *, data=None, key=None, info=None) -> Self:
        if data is None and info is None:
            return self.assign(active_key=key)

        key = key or self.metadata.active_key
        assert key is not None

        ret = self
        if data is not None:
            ret = ret.assign(ret.data.assign(**{key: data}), active_key=key)

        if info is not None:
            ret = ret.assign(var_infos=ret.metadata.var_infos | {key: info}, active_key=key)

        return ret

    @abstractmethod
    def compute(self) -> FullList: ...

    def coordss(self, key: SubdataKey | None = None) -> dict[DimKey, Coords]:
        return self.metadata.coordss

    def bounds(self, key: VarKey) -> Bounds:
        if key in self.coordss():
            coords = self.coordss()[key]
            delta = coords[1] - coords[0]
            return coords[0], coords[-1] + delta
        elif key in self.data:
            subdata = self[key]
            return dask.compute(subdata.min(skipna=True), subdata.max(skipna=True), traverse=False)
        else:
            raise RuntimeError(f"unknown key {key}")

    @property
    def dims(self) -> list[VarKey]:
        return list(self.data.columns)


class FullList(List[pd.DataFrame, pd.Series]):
    def compute(self) -> FullList:
        return self

    def dask_collections(self) -> list:
        return []


class LazyList(List[dd.DataFrame, dd.Series]):
    def compute(self) -> FullList:
        # partition_* describe the dask layout; meaningless after compute.
        return FullList(self.data.compute(), self.metadata.assign(partition_dim=None, partition_ranges=None))

    def dask_collections(self) -> list:
        return [self.data]
