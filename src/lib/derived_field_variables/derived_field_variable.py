import inspect
import typing

import xarray as xr

from ..file_util import FieldPrefix

__all__ = ["derived_field_variable", "derive_field_variable"]


class DeriveField(typing.Protocol):
    def __call__(self, *variables: xr.DataArray) -> xr.DataArray: ...


class DerivedFieldVariable:
    def __init__(
        self,
        name: str,
        base_var_names: list[str],
        derive: DeriveField,
    ):
        self.name = name
        self.base_var_names = base_var_names
        self.derive = derive

    def assign_to(self, ds: xr.Dataset):
        ds[self.name] = self.derive(*(ds[base_var_name] for base_var_name in self.base_var_names))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(({', '.join(self.base_var_names)}) -> {self.name}: {self.derive!r})"


DERIVED_FIELD_VARIABLES: dict[FieldPrefix, dict[str, DerivedFieldVariable]] = {}


def register_derived_field_variable(prefix: FieldPrefix, var: DerivedFieldVariable):
    DERIVED_FIELD_VARIABLES.setdefault(prefix, {})[var.name] = var


def derived_field_variable(prefix: FieldPrefix):
    def derived_field_variable_inner[F: (function, DeriveField)](derive_func: F) -> F:
        name = derive_func.__name__
        base_var_names = list(inspect.signature(derive_func).parameters)
        register_derived_field_variable(prefix, DerivedFieldVariable(name, base_var_names, derive_func))
        return derive_func

    return derived_field_variable_inner


def derive_field_variable(ds: xr.Dataset, var_name: str, ds_prefix: FieldPrefix):
    if var_name in ds.variables:
        return
    elif var_name in DERIVED_FIELD_VARIABLES[ds_prefix]:
        derived_var = DERIVED_FIELD_VARIABLES[ds_prefix][var_name]
        for base_var_name in derived_var.base_var_names:
            derive_field_variable(ds, base_var_name, ds_prefix)
        derived_var.assign_to(ds)
    else:
        message = f"No variable named '{var_name}'.\nThe following variables are defined: {list(ds.variables)}\n The following variables can be derived: {list(DERIVED_FIELD_VARIABLES[ds_prefix])}"
        raise ValueError(message)
