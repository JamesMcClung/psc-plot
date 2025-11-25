from __future__ import annotations

import typing
from abc import abstractmethod
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.animation import FuncAnimation
from matplotlib.projections.polar import PolarAxes

from lib.data.keys import SPATIAL_DIMS_KEY, TIME_DIM_KEY, VAR_LATEX_KEY
from lib.dimension import DIMENSIONS
from lib.parsing.fit import Fit
from lib.plotting import plt_util
from lib.plotting.plot import Plot


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


def get_extent(da: xr.DataArray, dim: str) -> tuple[float, float]:
    lower = da[dim][0]
    upper = da[dim][-1] + (da[dim][1] - da[dim][0])
    return (float(lower), float(upper))


class FieldAnimation2d(AnimatedPlot):
    def _init_fig(self):
        data = self._get_data_at_frame(0)

        # must set scale (log, linear) before making image
        self.ax.set_xscale(self.scales[1])
        self.ax.set_yscale(self.scales[2])

        self.im = self.ax.imshow(
            data,
            origin="lower",
            extent=(*get_extent(data, self.spatial_dims[0]), *get_extent(data, self.spatial_dims[1])),
            norm=self.scales[0],
        )

        self.fig.colorbar(self.im)
        data_lower, data_upper = self._get_var_bounds()
        plt_util.update_cbar(self.im, data_min_override=data_lower, data_max_override=data_upper)

        plt_util.update_title(self.ax, data.attrs[VAR_LATEX_KEY], DIMENSIONS[self.time_dim].get_coordinate_label(data[self.time_dim]))

        self.ax.set_aspect(1 / self.ax.get_data_ratio())
        self.ax.set_xlabel(DIMENSIONS[self.spatial_dims[0]].to_axis_label())
        self.ax.set_ylabel(DIMENSIONS[self.spatial_dims[1]].to_axis_label())

        self.fig.tight_layout()

    def _update_fig(self, frame: int):
        data = self._get_data_at_frame(frame)

        self.im.set_array(data)

        plt_util.update_title(self.ax, data.attrs[VAR_LATEX_KEY], DIMENSIONS[self.time_dim].get_coordinate_label(data[self.time_dim]))
        return [self.im, self.ax.title]

    def _get_data_at_frame(self, frame: int) -> xr.DataArray:
        data = super()._get_data_at_frame(frame)
        data = data.transpose(*reversed(self.spatial_dims))
        return data


class FieldAnimation2dPolar(AnimatedPlot):
    ax: PolarAxes

    def __init__(
        self,
        data: xr.DataArray,
        scales: list[plt_util.Scale],
    ):
        super().__init__(data, scales, subplot_kw={"projection": "polar"})

    def _init_fig(self):
        data = self._get_data_at_frame(0)

        # must set scale before making image
        self.ax.set_rscale(self.scales[1])

        vertices_theta = np.concat((data.coords[self.spatial_dims[1]].data, [2 * np.pi]))
        vertices_theta -= vertices_theta[1] / 2
        vertices_r = list(data.coords[self.spatial_dims[0]].data)
        vertices_r += [vertices_r[-1] + vertices_r[1]]

        self.im = self.ax.pcolormesh(
            *np.meshgrid(vertices_theta, vertices_r),
            data,
            shading="flat",
            norm=self.scales[0],
        )

        self.fig.colorbar(self.im)
        data_lower, data_upper = self._get_var_bounds()
        plt_util.update_cbar(self.im, data_min_override=data_lower, data_max_override=data_upper)

        plt_util.update_title(self.ax, data.attrs[VAR_LATEX_KEY], DIMENSIONS[self.time_dim].get_coordinate_label(data[self.time_dim]))

        # FIXME make the labels work
        # self.ax.set_xlabel(DIMENSIONS[self.dims[1]].to_axis_label())
        # self.ax.set_ylabel(DIMENSIONS[self.dims[0]].to_axis_label())

        self.fig.tight_layout()

    def _update_fig(self, frame: int):
        data = self._get_data_at_frame(frame)

        self.im.set_array(data)

        plt_util.update_title(self.ax, data.attrs[VAR_LATEX_KEY], DIMENSIONS[self.time_dim].get_coordinate_label(data[self.time_dim]))
        return [self.im, self.ax.title]


class FieldAnimation1d(AnimatedPlot):
    def __init__(
        self,
        data: xr.DataArray,
        *,
        scales: list[plt_util.Scale] = [],
        fits: list[Fit] = [],
        show_t0: bool = False,
    ):
        super().__init__(data, scales=scales)

        self.fits = fits
        self.show_t0 = show_t0

    def _init_fig(self):
        data = self._get_data_at_frame(0)
        xdata = data.coords[data.dims[0]]

        line_type = "-"

        if self.show_t0:
            self.ax.plot(xdata, data, "-", label=DIMENSIONS[self.time_dim].get_coordinate_label(self.data.coords[self.time_dim][0]))
            line_type = "--"

        if self.fits:
            line_type = "."

        [self.line] = self.ax.plot(xdata, data, line_type)

        plt_util.update_title(self.ax, data.attrs[VAR_LATEX_KEY], DIMENSIONS[self.time_dim].get_coordinate_label(data[self.time_dim]))
        self.ax.set_xlabel(DIMENSIONS[self.spatial_dims[0]].to_axis_label())
        self.ax.set_ylabel(f"${data.attrs[VAR_LATEX_KEY]}$")

        self.ax.set_xscale(self.scales[1])
        self.ax.set_yscale(self.scales[0])

        self.fit_lines = [fit.plot_fit(self.ax, data) for fit in self.fits]

        if self.fits or self.show_t0:
            self.ax.legend()

        self._update_ybounds()
        self.fig.tight_layout()

    def _update_fig(self, frame: int):
        data = self._get_data_at_frame(frame)

        self.line.set_ydata(data)

        for fit, line in zip(self.fits, self.fit_lines):
            # TODO properly add and remove lines from fits
            fit.update_fit(data, line)

        if self.fits:
            # updates legend in case fit labels changed (e.g. to show different fit params)
            self.ax.legend()

        plt_util.update_title(self.ax, data.attrs[VAR_LATEX_KEY], DIMENSIONS[self.time_dim].get_coordinate_label(data[self.time_dim]))
        return [self.line, self.ax.yaxis, self.ax.title]

    def _update_ybounds(self):
        ymin, ymax = plt_util.symmetrize_bounds(*self._get_var_bounds())
        self.ax.set_ybound(ymin, ymax)

    def add_fits(self, fits: list[Fit]):
        self.fits.extend(fits)
