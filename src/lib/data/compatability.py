from types import GenericAlias, UnionType
from typing import Any, TypeAliasType, _LiteralGenericAlias, get_args, get_origin


def isinstance2(val: Any, typelike: Any) -> bool:
    # TODO use PEP 747's TypeForm[T] and make this a TypeGuard[T]
    if isinstance(typelike, type):
        return isinstance(val, typelike)

    elif isinstance(typelike, UnionType):
        return any(isinstance2(val, t) for t in get_args(typelike))

    elif isinstance(typelike, GenericAlias):
        origin = get_origin(typelike)
        args = get_args(typelike)

        if origin is list and len(args) == 1:
            (elem_type,) = args
            return isinstance(val, list) and all(isinstance2(elem, elem_type) for elem in val)

        raise NotImplementedError(f"Unsupported generic: {typelike!r}")

    elif isinstance(typelike, TypeAliasType):
        return isinstance2(val, typelike.__value__)

    elif isinstance(typelike, _LiteralGenericAlias):
        return val in get_args(typelike)

    else:
        message = f"Unsupported type expression: {typelike!r}, of class {typelike.__class__!r}"
        raise NotImplementedError(message)
