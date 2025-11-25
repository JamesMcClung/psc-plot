import typing
from abc import abstractmethod
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.animation import FuncAnimation

from lib import plt_util
from lib.animation.plot import Plot
from lib.data.keys import SPATIAL_DIMS_KEY, TIME_DIM_KEY


class AnimatedPlot(Plot):
    def __init__(
        self,
        data: xr.DataArray,
        *,
        scales: list[plt_util.Scale] = [],
        subplot_kw: dict[str, typing.Any] = {},
    ):
        super().__init__(data)
        self.spatial_dims: list[str] = self.data.attrs[SPATIAL_DIMS_KEY]
        self.time_dim: str = self.data.attrs[TIME_DIM_KEY]
        self.scales = scales + ["linear"] * (1 + len(self.spatial_dims) - len(scales))
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

    def _get_data_at_frame(self, frame: int) -> xr.DataArray:
        return self.data.isel({self.time_dim: frame})

    def _get_var_bounds(self) -> tuple[float, float]:
        if self.scales[0] == "log":
            return np.exp(np.nanquantile(np.log(self.data), [0.5, 1])) * [0.1, 1.1]

        bounds = np.nanquantile(self.data, [0, 1])
        bounds *= 1 + 0.1 * np.array([-float(bounds[0] > 0), float(bounds[1] > 0)])
        return bounds
