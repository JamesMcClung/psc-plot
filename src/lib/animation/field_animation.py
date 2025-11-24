from __future__ import annotations

import typing

import numpy as np
import xarray as xr
from matplotlib.projections.polar import PolarAxes

from lib.parsing.fit import Fit

from .. import plt_util
from ..data.keys import SPATIAL_DIMS_KEY, TIME_DIM_KEY, VAR_LATEX_KEY
from ..data.source import DataSource
from ..dimension import DIMENSIONS
from .animation_base import Animation

__all__ = ["FieldAnimation"]


def get_extent(da: xr.DataArray, dim: str) -> tuple[float, float]:
    lower = da[dim][0]
    upper = da[dim][-1] + (da[dim][1] - da[dim][0])
    return (float(lower), float(upper))


class FieldAnimation(Animation):
    def __init__(
        self,
        steps: list[int],
        source: DataSource,
        scales: list[plt_util.Scale],
        *,
        subplot_kw: dict[str, typing.Any] = {},
    ):
        self.source = source
        self.data: xr.DataArray = source.get_data(steps)
        self.spatial_dims: list[str] = self.data.attrs[SPATIAL_DIMS_KEY]
        self.time_dim: str = self.data.attrs[TIME_DIM_KEY]
        nframes = len(self.data.coords[self.time_dim])
        self.scales = scales + ["linear"] * (1 + len(self.spatial_dims) - len(scales))

        super().__init__(nframes, subplot_kw=subplot_kw)

        self.indep_scale: plt_util.Scale = "linear"
        self.dep_scale: plt_util.Scale = "linear"

    def set_scale(self, indep_scale: plt_util.Scale, dep_scale: plt_util.Scale):
        self.indep_scale = indep_scale
        self.dep_scale = dep_scale

    def _get_data_at_frame(self, frame: int) -> xr.DataArray:
        return self.data.isel({self.time_dim: frame})

    def _get_var_bounds(self) -> tuple[float, float]:
        if self.dep_scale == "log":
            return np.exp(np.nanquantile(np.log(self.data), [0.5, 1])) * [0.1, 1.1]

        bounds = np.nanquantile(self.data, [0, 1])
        bounds *= 1 + 0.1 * np.array([-float(bounds[0] > 0), float(bounds[1] > 0)])
        return bounds

    @staticmethod
    def get_animation_type(spatial_dims: list[str]) -> type[FieldAnimation]:
        if len(spatial_dims) == 1:
            return FieldAnimation1d
        elif len(spatial_dims) == 2:
            if DIMENSIONS[spatial_dims[0]].geometry == "polar:r" and DIMENSIONS[spatial_dims[1]].geometry == "polar:theta":
                return FieldAnimation2dPolar
            else:
                return FieldAnimation2d
        else:
            raise NotImplementedError("don't have 3D animations yet")

    def _get_default_save_path(self) -> str:
        return "-".join(self.source.get_name_fragments()) + ".mp4"


class FieldAnimation2d(FieldAnimation):
    def _init_fig(self):
        data = self._get_data_at_frame(0)

        # must set scale (log, linear) before making image
        self.ax.set_xscale(self.indep_scale)
        self.ax.set_yscale(self.indep_scale)

        self.im = self.ax.imshow(
            data,
            origin="lower",
            extent=(*get_extent(data, self.spatial_dims[0]), *get_extent(data, self.spatial_dims[1])),
            norm=self.dep_scale,
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


class FieldAnimation2dPolar(FieldAnimation):
    ax: PolarAxes

    def __init__(
        self,
        steps: list[int],
        source: DataSource,
        scales: list[plt_util.Scale],
    ):
        super().__init__(steps, source, scales, subplot_kw={"projection": "polar"})

    def _init_fig(self):
        data = self._get_data_at_frame(0)

        # must set scale (log, linear) before making image
        if self.indep_scale == "log":
            self.ax.set_rscale("symlog")

        vertices_theta = np.concat((data.coords[self.spatial_dims[1]].data, [2 * np.pi]))
        vertices_theta -= vertices_theta[1] / 2
        vertices_r = list(data.coords[self.spatial_dims[0]].data)
        vertices_r += [vertices_r[-1] + vertices_r[1]]

        self.im = self.ax.pcolormesh(
            *np.meshgrid(vertices_theta, vertices_r),
            data,
            shading="flat",
            norm=self.dep_scale,
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


class FieldAnimation1d(FieldAnimation):
    def __init__(
        self,
        steps: list[int],
        source: DataSource,
    ):
        super().__init__(steps, source)

        self.fits: list[Fit] = []
        self.show_t0 = False

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

        self.ax.set_xscale(self.indep_scale)
        self.ax.set_yscale(self.dep_scale)

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
