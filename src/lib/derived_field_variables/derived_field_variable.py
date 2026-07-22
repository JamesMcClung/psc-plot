import inspect
import typing

import xarray as xr

from lib.data.data_with_attrs import Field
from lib.var_info_registry import lookup

__all__ = ["derived_field_variable", "derive_field_variable"]


class DeriveField(typing.Protocol):
    def __call__(self, *variables: xr.DataArray) -> xr.DataArray: ...


class DerivedFieldVariable:
    def __init__(
        self,
        name: str,
        base_var_names: list[str],
        derive: DeriveField,
        prefix: str,
    ):
        self.name = name
        self.base_var_names = base_var_names
        self.derive = derive
        self.prefix = prefix

    def assign_to(self, field: Field) -> Field:
        da = self.derive(*(field.data[base_var_name] for base_var_name in self.base_var_names))
        new_data = field.data | {self.name: da}
        new_var_infos = field.metadata.var_infos | {key: lookup(self.prefix, key) for key in (self.name, *da.dims)}
        return field.assign_data(new_data).assign_metadata(var_infos=new_var_infos)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(({', '.join(self.base_var_names)}) -> {self.name}: {self.derive!r})"


DERIVED_FIELD_VARIABLES: dict[str, dict[str, DerivedFieldVariable]] = {}


def register_derived_field_variable(prefix: str, var: DerivedFieldVariable):
    DERIVED_FIELD_VARIABLES.setdefault(prefix, {})[var.name] = var


def derived_field_variable(prefix: str):
    def derived_field_variable_inner[F: (function, DeriveField)](derive_func: F) -> F:
        name = derive_func.__name__
        base_var_names = list(inspect.signature(derive_func).parameters)
        register_derived_field_variable(prefix, DerivedFieldVariable(name, base_var_names, derive_func, prefix))
        return derive_func

    return derived_field_variable_inner


def derive_field_variable(field: Field, active_key: str, ds_prefix: str) -> Field:
    if active_key in field.data:
        return field
    elif active_key in DERIVED_FIELD_VARIABLES[ds_prefix]:
        derived_var = DERIVED_FIELD_VARIABLES[ds_prefix][active_key]
        for base_var_name in derived_var.base_var_names:
            field = derive_field_variable(field, base_var_name, ds_prefix)
        return derived_var.assign_to(field)
    else:
        message = f"""No variable named '{active_key}'.
The following variables are defined:    {list(field.data)}.
The following variables can be derived: {list(DERIVED_FIELD_VARIABLES[ds_prefix])}."""
        raise ValueError(message)
