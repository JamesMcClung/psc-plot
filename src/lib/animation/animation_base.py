import typing
from abc import abstractmethod
from pathlib import Path

import matplotlib.pyplot as plt
import xarray as xr
from matplotlib.animation import FuncAnimation

from lib.animation.plot import Plot
from lib.data.keys import SPATIAL_DIMS_KEY, TIME_DIM_KEY
from lib.data.source import DataSource


class AnimatedPlot(Plot):
    def __init__(self, source: DataSource, data: xr.DataArray, *, subplot_kw: dict[str, typing.Any] = {}):
        self.source = source
        self.data = data
        self.spatial_dims: list[str] = self.data.attrs[SPATIAL_DIMS_KEY]
        self.time_dim: str = self.data.attrs[TIME_DIM_KEY]
        nframes = len(self.data.coords[self.time_dim])

        self.fig, self.ax = plt.subplots(subplot_kw=subplot_kw)
        self._initialized = False

        # FIXME get blitting to work with the title
        # note: blitting doesn't seem to affect saved animations, only ones displayed with plt.show
        self.anim = FuncAnimation(self.fig, self._update_fig, frames=nframes, blit=False)

    @abstractmethod
    def _init_fig(self): ...

    @abstractmethod
    def _update_fig(self, frame: int): ...

    def show(self):
        if not self._initialized:
            self._init_fig()
            self._initialized = True
        plt.show()

    def save(self, path_override: Path | None = None):
        if not self._initialized:
            self._init_fig()
            self._initialized = True
        path = path_override or "-".join(self.source.get_name_fragments()) + ".mp4"
        self.anim.save(path)
