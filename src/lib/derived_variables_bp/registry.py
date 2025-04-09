import inspect

from ..file_util import BpPrefix
from .derived_variable_bp import DeriveBp, DerivedVariableBp

__all__ = ["derived_variable_bp", "DERIVED_VARIABLE_BP_REGISTRY", "register_derived_variable_bp"]

DERIVED_VARIABLE_BP_REGISTRY: dict[BpPrefix, dict[str, DerivedVariableBp]] = {}


def register_derived_variable_bp(prefix: BpPrefix, var: DerivedVariableBp):
    DERIVED_VARIABLE_BP_REGISTRY.setdefault(prefix, {})[var.name] = var


def derived_variable_bp(prefix: BpPrefix):
    def derived_variable_bp_inner[F: (function, DeriveBp)](derive_func: F) -> F:
        name = derive_func.__name__
        base_var_names = list(inspect.signature(derive_func).parameters)
        register_derived_variable_bp(prefix, DerivedVariableBp(name, base_var_names, derive_func))
        return derive_func

    return derived_variable_bp_inner
