import numpy as np
import xarray as xr

from .. import bp_util, file_util, plt_util
from ..bp_util import DEFAULT_SPACE_UNIT_LATEX, DEFAULT_TIME_UNIT_LATEX, BpDim
from .animation_base import Animation

__all__ = ["BpAnimation2d", "BpAnimation1d"]


def get_extent(da: xr.DataArray, dim: BpDim) -> tuple[float, float]:
    dim_idx = ["x", "y", "z"].index(dim)
    lower = da.corner[dim_idx]
    upper = lower + da.length[dim_idx]
    return (lower, upper)


class BpAnimation2d(Animation):
    def __init__(self, steps: list[int], prefix: file_util.BpPrefix, variable: str, dims: tuple[BpDim, BpDim]):
        super().__init__(steps)

        self.prefix = prefix
        self.variable = variable
        self.dims = dims

        data = self._load_data(self.steps[0])

        left_right_bottom_top = (*get_extent(data, self.dims[0]), *get_extent(data, self.dims[1]))
        self.im = self.ax.imshow(data, origin="lower", extent=left_right_bottom_top)

        self.fig.colorbar(self.im)
        plt_util.update_cbar(self.im)

        plt_util.update_title(self.ax, self.variable, data.time, DEFAULT_TIME_UNIT_LATEX)
        self.ax.set_aspect(1 / self.ax.get_data_ratio())
        self.ax.set_xlabel(f"${self.dims[0]}$ [{DEFAULT_SPACE_UNIT_LATEX}]")
        self.ax.set_ylabel(f"${self.dims[1]}$ [{DEFAULT_SPACE_UNIT_LATEX}]")

    def _update_fig(self, step: int):
        data = self._load_data(step)

        self.im.set_array(data)

        plt_util.update_title(self.ax, self.variable, data.time, DEFAULT_TIME_UNIT_LATEX)
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
        xdata = np.linspace(*get_extent(data, dim), len(data), endpoint=False)

        [self.line] = self.ax.plot(xdata, data)
        self._update_ybounds(data)

        plt_util.update_title(self.ax, self.variable, data.time, DEFAULT_TIME_UNIT_LATEX)
        self.ax.set_xlabel(f"{self.dim} [{DEFAULT_SPACE_UNIT_LATEX}]")
        self.ax.set_ylabel(f"{self.variable}")

    def _update_fig(self, step: int):
        data = self._load_data(step)

        self.line.set_ydata(data)
        self._update_ybounds(data)

        plt_util.update_title(self.ax, self.variable, data.time, DEFAULT_TIME_UNIT_LATEX)
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
