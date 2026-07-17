from __future__ import annotations

from abc import ABC, abstractmethod

from lib.data.adaptors.idx import Idx
from lib.data.data_with_attrs import DataWithAttrs
from lib.data.plot_target import PlotTarget
from lib.plotting.plot_info import PlotInfo


class Renderer[Data: DataWithAttrs](ABC):
    def __init__(self, full_data: Data, plot_target: PlotTarget):
        self.full_data = full_data
        self.plot_target = plot_target
        self.plot_info = self.init_plot_info()

    def _get_data_at_frame(self, frame: int) -> Data:
        if self.plot_target.time_dim:
            return Idx({self.plot_target.time_dim: frame}).apply(self.full_data)
        return self.full_data

    @abstractmethod
    def init_plot_info(self) -> PlotInfo: ...

    @abstractmethod
    def update_plot_info(self, frame: int): ...
