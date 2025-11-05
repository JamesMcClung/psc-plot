import inspect

from ..file_util import FieldPrefix
from .derived_field_variable import DerivedFieldVariable, DeriveField

__all__ = ["derived_field_variable", "DERIVED_VARIABLE_BP_REGISTRY", "register_derived_field_variable"]

DERIVED_VARIABLE_BP_REGISTRY: dict[FieldPrefix, dict[str, DerivedFieldVariable]] = {}


def register_derived_field_variable(prefix: FieldPrefix, var: DerivedFieldVariable):
    DERIVED_VARIABLE_BP_REGISTRY.setdefault(prefix, {})[var.name] = var


def derived_field_variable(prefix: FieldPrefix):
    def derived_field_variable_inner[F: (function, DeriveField)](derive_func: F) -> F:
        name = derive_func.__name__
        base_var_names = list(inspect.signature(derive_func).parameters)
        register_derived_field_variable(prefix, DerivedFieldVariable(name, base_var_names, derive_func))
        return derive_func

    return derived_field_variable_inner
