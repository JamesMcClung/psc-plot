import inspect
import typing

import pandas as pd

from ..file_util import ParticlePrefix

__all__ = ["derived_particle_variable", "derive_particle_variable", "DERIVED_PARTICLE_VARIABLES"]


class DeriveParticleVariable(typing.Protocol):
    def __call__(self, *variables: pd.Series) -> pd.Series: ...


class DerivedParticleVariable:
    def __init__(
        self,
        name: str,
        base_var_names: list[str],
        derive: DeriveParticleVariable,
    ):
        self.name = name
        self.base_var_names = base_var_names
        self.derive = derive

    def assign_to(self, df: pd.DataFrame):
        df[self.name] = self.derive(*(df[base_var_name] for base_var_name in self.base_var_names))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(({', '.join(self.base_var_names)}) -> {self.name}: {self.derive!r})"


DERIVED_PARTICLE_VARIABLES: dict[ParticlePrefix, dict[str, DerivedParticleVariable]] = {}


def register_derived_particle_variable(prefix: ParticlePrefix, var: DerivedParticleVariable):
    DERIVED_PARTICLE_VARIABLES.setdefault(prefix, {})[var.name] = var


def derived_particle_variable(prefix: ParticlePrefix):
    def derived_particle_variable_inner[F: (function, DeriveParticleVariable)](derive_func: F) -> F:
        name = derive_func.__name__
        base_var_names = list(inspect.signature(derive_func).parameters)
        register_derived_particle_variable(prefix, DerivedParticleVariable(name, base_var_names, derive_func))
        return derive_func

    return derived_particle_variable_inner


def derive_particle_variable(df: pd.DataFrame, var_name: str, ds_prefix: ParticlePrefix):
    if var_name in df.columns:
        return
    elif var_name in DERIVED_PARTICLE_VARIABLES[ds_prefix]:
        derived_var = DERIVED_PARTICLE_VARIABLES[ds_prefix][var_name]
        for base_var_name in derived_var.base_var_names:
            derive_particle_variable(df, base_var_name, ds_prefix)
        derived_var.assign_to(df)
    else:
        message = f"No variable named '{var_name}'.\nThe following variables are defined: {list(df.columns)}\n The following variables can be derived: {list(DERIVED_PARTICLE_VARIABLES[ds_prefix])}"
        raise ValueError(message)
