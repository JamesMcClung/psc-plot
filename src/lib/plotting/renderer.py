from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from lib.data.data_with_attrs import DataWithAttrs


class Renderer[Data: DataWithAttrs](ABC):
    def subplot_kw(self) -> dict[str, Any]:
        return {}

    @abstractmethod
    def make_init_data(self, fig: Figure, ax: Axes, frame_data: Data) -> Any:
        ...

    @abstractmethod
    def init(self, fig: Figure, ax: Axes, full_data: Data, frame_data: Data, init_data: Any) -> None:
        ...

    def make_update_data(self, ax: Axes, frame_data: Data) -> Any:
        return None

    def draw(self, ax: Axes, frame_data: Data, update_data: Any) -> None:
        pass
