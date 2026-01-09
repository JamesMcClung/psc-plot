from types import UnionType
from typing import TypeVar


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
