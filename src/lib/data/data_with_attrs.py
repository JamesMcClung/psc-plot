from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from functools import cached_property
from typing import Any, Self

import dask.dataframe as dd
import numpy as np
import pandas as pd
import xarray as xr


@dataclass(kw_only=True, frozen=True)
class Metadata:
    var_name: str
    var_latex: str
    name_fragments: list[str] = field(default_factory=list)

    spatial_dims: list[str] = field(default_factory=list)
    time_dim: str | None = None
    color_dim: str | None = None

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

    def __init__(self, data: D, metadata: MD):
        object.__setattr__(self, "data", data)
        object.__setattr__(self, "metadata", metadata)

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


@dataclass(kw_only=True, frozen=True)
class FieldMetadata(Metadata):
    pass


class Field(DataWithAttrs[xr.DataArray, FieldMetadata]):
    data: xr.DataArray
    metadata: FieldMetadata

    @cached_property
    def coordss(self) -> dict[str, np.ndarray]:
        return {dim: np.array(self.data.coords[dim]) for dim in self.data.coords.keys()}

    @cached_property
    def dims(self) -> list[str]:
        return list(self.data.dims)


@dataclass(kw_only=True, frozen=True)
class ListMetadata(Metadata):
    coordss: dict[str, np.ndarray] = field(default_factory=dict)
    dependent_var: str | None = None
    weight_var: str | None = None


class List[D: pd.DataFrame | dd.DataFrame](DataWithAttrs[D, ListMetadata]):
    data: pd.DataFrame | dd.DataFrame
    metadata: ListMetadata

    @property
    def coordss(self) -> dict[str, np.ndarray]:
        return self.metadata.coordss

    @property
    def dims(self) -> list[str]:
        return list(self.data.columns)


class FullList(List[pd.DataFrame]):
    data: pd.DataFrame


class LazyList(List[dd.DataFrame]):
    data: dd.DataFrame

    def compute(self) -> FullList:
        return FullList(self.data.compute(), self.metadata)
