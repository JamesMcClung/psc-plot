from dataclasses import dataclass
from typing import Any, TypeGuard

from matplotlib.axes import Axes

from lib.data.compatability import isinstance2
from lib.data.data_with_attrs import Field, FullList, List
from lib.plotting.hook import Hook


def check_impl[T](data: Any, data_type: type[T]) -> TypeGuard[T]:
    for superclass in data_type.mro():
        if not hasattr(superclass, "__annotations__"):
            continue

        for field_name, field_type in superclass.__annotations__.items():
            if not hasattr(data, field_name):
                return False

            if not isinstance2(getattr(data, field_name), field_type):
                return False

    return True


def assert_impl[T](data: Any, required_type: type[T]) -> T:
    if not check_impl(data, required_type):
        raise TypeError("TODO better message")
    return data


@dataclass(kw_only=True)
class HasData:
    data: Field | List


@dataclass(kw_only=True)
class HasFieldData:
    data: Field


@dataclass(kw_only=True)
class HasListData:
    data: List


@dataclass(kw_only=True)
class HasFullListData:
    data: FullList


@dataclass(kw_only=True)
class HasLineType:
    line_type: str


@dataclass(kw_only=True)
class HasAxes:
    axes: Axes


@dataclass(kw_only=True)
class HasHookList:
    hooks: list[Hook]
