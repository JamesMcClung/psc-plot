from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from lib.data.data_with_attrs import DataWithAttrs
from lib.plotting.plot_info import PlotInfo


class Renderer[Data: DataWithAttrs](ABC):
    def subplot_kw(self) -> dict[str, Any]:
        return {}

    @abstractmethod
    def make_init_data(self, fig: Figure, ax: Axes, frame_data: Data) -> Any: ...

    def make_update_data(self, ax: Axes, frame_data: Data) -> Any:
        return None

    @abstractmethod
    def init_plot_info(self, full_data: Data, frame_data: Data) -> PlotInfo: ...

    @abstractmethod
    def update_plot_info(self, frame_data: Data): ...
