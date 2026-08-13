import inspect
import typing

import pandas as pd

from lib import var_info_registry
from lib.data.data_with_attrs import List
from lib.data.types import SubdataKey

__all__ = ["derived_particle_variable", "derive_particle_variable"]


class DeriveParticleVariable(typing.Protocol):
    def __call__(self, *variables: pd.Series) -> pd.Series: ...


class DerivedParticleVariable:
    def __init__(
        self,
        key: SubdataKey,
        base_var_keys: list[SubdataKey],
        derive: DeriveParticleVariable,
    ):
        self.key = key
        self.base_var_key = base_var_keys
        self.derive = derive

    def assign_to(self, data: List) -> List:
        df = data.data

        info = var_info_registry.lookup("prt", self.key)
        new_var_infos = {**data.metadata.var_infos, self.key: info}
        return data.assign(
            df.assign(**{self.key: self.derive(*(df[base_var_name] for base_var_name in self.base_var_key))}),
            var_infos=new_var_infos,
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(({', '.join(self.base_var_key)}) -> {self.key}: {self.derive!r})"


DERIVED_PARTICLE_VARIABLES: dict[str, dict[SubdataKey, DerivedParticleVariable]] = {}


def register_derived_particle_variable(prefix: str, var: DerivedParticleVariable):
    DERIVED_PARTICLE_VARIABLES.setdefault(prefix, {})[var.key] = var


def get_derived_particle_variables(prefix: str) -> dict[SubdataKey, DerivedParticleVariable]:
    if prefix.startswith("prt."):
        # FIXME this is a hardcoded hack
        prefix = "prt"
    return DERIVED_PARTICLE_VARIABLES[prefix]


def derived_particle_variable(prefix: str):
    def derived_particle_variable_inner[F: (function, DeriveParticleVariable)](derive_func: F) -> F:
        name = derive_func.__name__
        base_var_names = list(inspect.signature(derive_func).parameters)
        register_derived_particle_variable(prefix, DerivedParticleVariable(name, base_var_names, derive_func))
        return derive_func

    return derived_particle_variable_inner


def derive_particle_variable(data: List, active_key: SubdataKey, ds_prefix: str) -> List:
    if active_key in data:
        return data

    derived_vars = get_derived_particle_variables(ds_prefix)

    if active_key in derived_vars:
        derived_var = derived_vars[active_key]
        for base_var_name in derived_var.base_var_key:
            data = derive_particle_variable(data, base_var_name, ds_prefix)
        return derived_var.assign_to(data)
    else:
        message = f"""No variable named '{active_key}'.
The following variables are defined:    {data.dims}.
The following variables can be derived: {list(derived_vars)}."""
        raise ValueError(message)
