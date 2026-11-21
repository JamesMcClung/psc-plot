from __future__ import annotations

from abc import ABC, abstractmethod

from lib.data.adaptors.idx import Idx
from lib.data.data_with_attrs import DataWithAttrs
from lib.data.plot_target import PlotTarget, SpatialDims
from lib.data.types import VarKey
from lib.plotting.plot_info import PlotInfo


class Renderer[D: DataWithAttrs = DataWithAttrs, SD: SpatialDims = SpatialDims, PI: PlotInfo = PlotInfo](ABC):
    def __init__(self, plot_target: PlotTarget[D, SD]):
        self.plot_target = plot_target
        self.plot_info = self._init_plot_info()
        self.plot_info.frames_scalar_coord_values = [self.get_scalar_coord_values(frame) for frame in range(self.get_n_frames())]

    def _get_data_at_frame(self, frame: int) -> D:
        if self.plot_target.time_dim:
            frame = min(frame, self.get_n_frames() - 1)
            return Idx({self.plot_target.time_dim: frame}).apply(self.plot_target.data)
        return self.plot_target.data

    def get_scalar_coord_values(self, frame: int) -> dict[VarKey, float]:
        """The values of the coords that are scalar on `frame` (e.g. the time), without computing any data."""
        return {dim: coord for dim, coord in self._get_data_at_frame(frame).coordss().items() if coord.shape == ()}

    def get_n_frames(self) -> int:
        if self.plot_target.time_dim:
            return len(self.plot_target.data.coordss()[self.plot_target.time_dim])
        return 1

    @abstractmethod
    def _init_plot_info(self) -> PI: ...

    @abstractmethod
    def update_plot_info(self, frame: int): ...
