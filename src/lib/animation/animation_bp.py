import numpy as np
import xarray as xr

from .. import bp_util, file_util, plt_util
from ..bp_util import BpDim
from .animation_base import Animation

__all__ = ["BpAnimation2d", "BpAnimation1d"]


class BpAnimation2d(Animation):
    def __init__(self, steps: list[int], prefix: file_util.BpPrefix, variable: str, dims: tuple[BpDim, BpDim]):
        super().__init__(steps)

        self.prefix = prefix
        self.variable = variable
        self.dims = dims

        data = self._load_data(self.steps[0])

        self.im = self.ax.imshow(data, origin="lower")

        self.fig.colorbar(self.im)
        plt_util.update_cbar(self.im)

        plt_util.update_title(self.ax, self.variable, data.time)
        self.ax.set_aspect(1 / self.ax.get_data_ratio())
        self.ax.set_xlabel(f"{self.dims[0]} index")
        self.ax.set_ylabel(f"{self.dims[1]} index")

    def _update_fig(self, step: int):
        data = self._load_data(step)

        self.im.set_array(data)

        plt_util.update_title(self.ax, self.variable, data.time)
        plt_util.update_cbar(self.im)
        return [self.im, self.ax.title]

    def _load_data(self, step: int) -> xr.DataArray:
        ds = bp_util.load_ds(self.prefix, step)
        da = ds[self.variable]

        for dim in da.dims:
            if dim not in self.dims:
                da = da.reduce(np.mean, dim)

        # reverse order because imshow expects (y, x) order
        da = da.transpose(*reversed(self.dims), transpose_coords=True)

        da = da.assign_attrs(**ds.attrs)

        return da


class BpAnimation1d(Animation):
    def __init__(self, steps: list[int], prefix: file_util.BpPrefix, variable: str, dim: BpDim):
        super().__init__(steps)

        self.prefix = prefix
        self.variable = variable
        self.dim = dim

        data = self._load_data(self.steps[0])

        [self.line] = self.ax.plot(data)
        self._update_ybounds(data)

        plt_util.update_title(self.ax, self.variable, data.time)
        self.ax.set_xlabel(f"{self.dim} index")
        self.ax.set_ylabel(f"{self.variable}")

    def _update_fig(self, step: int):
        data = self._load_data(step)

        self.line.set_ydata(data)
        self._update_ybounds(data)

        plt_util.update_title(self.ax, self.variable, data.time)
        return [self.line, self.ax.yaxis, self.ax.title]

    def _load_data(self, step: int) -> xr.DataArray:
        ds = bp_util.load_ds(self.prefix, step)
        da = ds[self.variable]

        for dim in da.dims:
            if dim != self.dim:
                da = da.reduce(np.mean, dim)

        da = da.assign_attrs(**ds.attrs)

        return da

    def _update_ybounds(self, data: xr.DataArray):
        ymin, ymax = np.min(data), np.max(data)
        if ymin == ymax:
            ymin -= 0.1
            ymax += 0.1
        self.ax.set_ybound(ymin, ymax)
