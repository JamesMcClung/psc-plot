from __future__ import annotations

from abc import ABC, abstractmethod

from lib.data.adaptors.idx import Idx
from lib.data.data_with_attrs import DataWithAttrs, Field
from lib.data.plot_target import PlotTarget
from lib.plotting.plot_info import PlotInfo


class Renderer[Data: DataWithAttrs](ABC):
    def __init__(self, full_data: Data, plot_target: PlotTarget):
        self.plot_target = plot_target

        if isinstance(full_data, Field):
            self.full_data = full_data.assign_metadata(active_key=plot_target.color_dim or plot_target.spatial_dims.y_dim)
        else:
            self.full_data = full_data

        self.plot_info = self.init_plot_info()

    def _get_data_at_frame(self, frame: int) -> Data:
        if self.plot_target.time_dim:
            frame = min(frame, self.get_n_frames() - 1)
            return Idx({self.plot_target.time_dim: frame}).apply(self.full_data)
        return self.full_data

    def get_n_frames(self) -> int:
        if self.plot_target.time_dim:
            return len(self.full_data.coordss[self.plot_target.time_dim])
        return 1

    @abstractmethod
    def init_plot_info(self) -> PlotInfo: ...

    @abstractmethod
    def update_plot_info(self, frame: int): ...
