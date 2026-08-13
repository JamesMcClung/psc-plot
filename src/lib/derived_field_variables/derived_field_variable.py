import inspect
import typing

import xarray as xr

from lib.data.data_with_attrs import Field
from lib.data.types import SubdataKey
from lib.var_info_registry import lookup

__all__ = ["derived_field_variable", "derive_field_variable"]


class DeriveField(typing.Protocol):
    def __call__(self, *variables: xr.DataArray) -> xr.DataArray: ...


class DerivedFieldVariable:
    def __init__(
        self,
        key: SubdataKey,
        base_var_keys: list[SubdataKey],
        derive: DeriveField,
        prefix: str,
    ):
        self.key = key
        self.base_var_keys = base_var_keys
        self.derive = derive
        self.prefix = prefix

    def assign_to(self, field: Field) -> Field:
        da = self.derive(*(field.data[base_var_name] for base_var_name in self.base_var_keys))
        new_data = field.data | {self.key: da}
        new_var_infos = field.metadata.var_infos | {var_key: lookup(self.prefix, var_key) for var_key in (self.key, *da.dims)}
        return field.assign(new_data, var_infos=new_var_infos)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(({', '.join(self.base_var_keys)}) -> {self.key}: {self.derive!r})"


DERIVED_FIELD_VARIABLES: dict[str, dict[SubdataKey, DerivedFieldVariable]] = {}


def register_derived_field_variable(prefix: str, var: DerivedFieldVariable):
    DERIVED_FIELD_VARIABLES.setdefault(prefix, {})[var.key] = var


def derived_field_variable(prefix: str):
    def derived_field_variable_inner[F: (function, DeriveField)](derive_func: F) -> F:
        name = derive_func.__name__
        base_var_names = list(inspect.signature(derive_func).parameters)
        register_derived_field_variable(prefix, DerivedFieldVariable(name, base_var_names, derive_func, prefix))
        return derive_func

    return derived_field_variable_inner


def derive_field_variable(field: Field, active_key: SubdataKey, ds_prefix: str) -> Field:
    if active_key in field:
        return field
    elif active_key in DERIVED_FIELD_VARIABLES[ds_prefix]:
        derived_var = DERIVED_FIELD_VARIABLES[ds_prefix][active_key]
        for base_var_name in derived_var.base_var_keys:
            field = derive_field_variable(field, base_var_name, ds_prefix)
        return derived_var.assign_to(field)
    else:
        message = f"""No variable named '{active_key}'.
The following variables are defined:    {list(field.data)}.
The following variables can be derived: {list(DERIVED_FIELD_VARIABLES[ds_prefix])}."""
        raise ValueError(message)
