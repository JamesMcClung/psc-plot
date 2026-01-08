from typing import Protocol, runtime_checkable

from matplotlib.axes import Axes

from lib.data.data_with_attrs import Field, FullList, List


@runtime_checkable
class HasData(Protocol):
    data: Field | List


@runtime_checkable
class HasFieldData(Protocol):
    data: Field


@runtime_checkable
class HasListData(Protocol):
    data: List


@runtime_checkable
class HasFullListData(Protocol):
    data: FullList


@runtime_checkable
class HasLineType(Protocol):
    line_type: str


@runtime_checkable
class HasAxes(Protocol):
    axes: Axes
