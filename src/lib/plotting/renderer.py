from __future__ import annotations

from abc import ABC, abstractmethod

from lib.data.adaptors.idx import Idx
from lib.data.data_with_attrs import DataWithAttrs
from lib.data.plot_target import PlotTarget, SpatialDims
from lib.plotting.plot_info import PlotInfo


class Renderer[D: DataWithAttrs = DataWithAttrs, SD: SpatialDims = SpatialDims, PI: PlotInfo = PlotInfo](ABC):
    def __init__(self, plot_target: PlotTarget[D, SD]):
        self.plot_target = plot_target
        self.plot_info = self._init_plot_info()

    def _get_data_at_frame(self, frame: int) -> D:
        if self.plot_target.time_dim:
            frame = min(frame, self.get_n_frames() - 1)
            return Idx({self.plot_target.time_dim: frame}).apply(self.plot_target.data)
        return self.plot_target.data

    def get_n_frames(self) -> int:
        if self.plot_target.time_dim:
            return len(self.plot_target.data.coordss()[self.plot_target.time_dim])
        return 1

    @abstractmethod
    def _init_plot_info(self) -> PI: ...

    @abstractmethod
    def update_plot_info(self, frame: int): ...
