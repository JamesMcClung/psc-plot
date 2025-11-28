from __future__ import annotations

import typing
from abc import abstractmethod
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from lib.data.keys import SPATIAL_DIMS_KEY, TIME_DIM_KEY
from lib.plotting import plt_util
from lib.plotting.plot import DataWithAttrs, Plot


class AnimatedPlot[Data: DataWithAttrs](Plot[Data]):
    def __init__(
        self,
        data: Data,
        *,
        scales: list[plt_util.Scale] = [],
        subplot_kw: dict[str, typing.Any] = {},
    ):
        super().__init__(data)
        self.spatial_dims: list[str] = self.data.attrs[SPATIAL_DIMS_KEY]
        self.time_dim: str = self.data.attrs[TIME_DIM_KEY]
        self.scales = scales + ["linear"] * (1 + len(self.spatial_dims) - len(scales))

        self.fig, self.ax = plt.subplots(subplot_kw=subplot_kw)
        self._initialized = False

        # FIXME get blitting to work with the title
        # note: blitting doesn't seem to affect saved animations, only ones displayed with plt.show
        self.anim = FuncAnimation(self.fig, self._update_fig, frames=self._get_nframes(), blit=False)

    @abstractmethod
    def _get_nframes(self) -> int:
        """Calculate the number of frames. May assume everything except self.anim is initialized."""

    @abstractmethod
    def _init_fig(self): ...

    @abstractmethod
    def _update_fig(self, frame: int): ...

    def _initialize(self):
        if not self._initialized:
            self._init_fig()
            self._initialized = True

    def show(self):
        self._initialize()
        plt.show()

    def _get_save_ext(self):
        return ".mp4"

    def _save_to_path(self, path: Path):
        self._initialize()
        self.anim.save(path)
