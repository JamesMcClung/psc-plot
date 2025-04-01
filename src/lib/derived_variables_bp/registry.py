import inspect

from .derived_variable_bp import DeriveBp, DerivedVariableBp

__all__ = ["derived_variable_bp", "DERIVED_VARIABLE_BP_REGISTRY"]

DERIVED_VARIABLE_BP_REGISTRY: dict[str, DerivedVariableBp] = {}


def derived_variable_bp[F: (function, DeriveBp)](derive_func: F) -> F:
    name = derive_func.__name__
    base_var_names = list(inspect.signature(derive_func).parameters)
    DERIVED_VARIABLE_BP_REGISTRY[name] = DerivedVariableBp(name, base_var_names, derive_func)
    return derive_func
