from types import GenericAlias, UnionType
from typing import (
    Any,
    TypeAliasType,
    TypeVar,
    _LiteralGenericAlias,
    get_args,
    get_origin,
)


class DataError(Exception): ...


def ensure_type[Data](consumer_name: str, data: Data, *allowed_types: type):
    if not isinstance(data, allowed_types):
        names_of_types = ", ".join(f"{t.__module__}.{t.__name__}" for t in allowed_types)
        message = f"{consumer_name} accepts only the following types: [{names_of_types}], but received data of type {data.__class__.__module__}.{data.__class__.__name__}"
        raise DataError(message)


def get_allowed_types(type_annotation) -> list[type]:
    if isinstance(type_annotation, type):
        return [type_annotation]
    elif isinstance(type_annotation, UnionType):
        return type_annotation.__args__
    elif isinstance(type_annotation, TypeVar):
        return get_allowed_types(type_annotation.__bound__)
    else:
        message = f"not sure how to find allowed types for the following type annotation: {type_annotation}"
        raise NotImplementedError(message)


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
