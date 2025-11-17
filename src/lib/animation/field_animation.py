from __future__ import annotations

import typing

import numpy as np
import xarray as xr
from matplotlib.projections.polar import PolarAxes

from lib.parsing.fit import Fit

from .. import plt_util
from ..dimension import DIMENSIONS
from ..field_source import FieldSource
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
        source: FieldSource,
        time_dim: str,
        *,
        subplot_kw: dict[str, typing.Any] = {},
    ):
        self.source = source
        self.time_dim = time_dim
        self.data = source.get_data(steps)
        self.nframes = len(self.data.coords[time_dim])

        self.indep_scale: plt_util.Scale = "linear"
        self.dep_scale: plt_util.Scale = "linear"

        # TODO: fix steps vs frames
        super().__init__(list(range(self.nframes)), subplot_kw=subplot_kw)

    def set_scale(self, indep_scale: plt_util.Scale, dep_scale: plt_util.Scale):
        self.indep_scale = indep_scale
        self.dep_scale = dep_scale

    def _get_data_at_frame(self, frame: int) -> xr.DataArray:
        da = self.data.isel({self.time_dim: frame})

        # filter out near-zero values
        if self.dep_scale == "log":
            new_data_inner = da.data
            new_data_inner[new_data_inner < 1e-40] = np.nan
            da[:] = new_data_inner

        return da

    def _get_var_bounds(self) -> tuple[float, float]:
        return (np.nanmin(self.data), np.nanmax(self.data))

    @staticmethod
    def get_animation(
        steps: list[int],
        source: FieldSource,
        time_dim: str,
        spatial_dims: list[str],
    ) -> FieldAnimation:
        if len(spatial_dims) == 1:
            return FieldAnimation1d(steps, source, time_dim, spatial_dims[0])
        if len(spatial_dims) == 2:
            if DIMENSIONS[spatial_dims[0]].geometry == "polar:r" and DIMENSIONS[spatial_dims[1]].geometry == "polar:theta":
                return FieldAnimation2dPolar(steps, source, time_dim, tuple(spatial_dims))
            else:
                return FieldAnimation2d(steps, source, time_dim, tuple(spatial_dims))
        else:
            raise NotImplementedError("don't have 3D animations yet")

    def _get_default_save_path(self) -> str:
        return "-".join(self.source.get_name_fragments()) + ".mp4"


class FieldAnimation2d(FieldAnimation):
    def __init__(
        self,
        steps: list[int],
        source: FieldSource,
        time_dim: str,
        spatial_dims: tuple[str, str],
    ):
        super().__init__(steps, source, time_dim)

        self.spatial_dims = spatial_dims

    def _init_fig(self):
        data = self._get_data_at_frame(0)

        # must set scale (log, linear) before making image
        self.ax.set_xscale(self.indep_scale)
        self.ax.set_yscale(self.indep_scale)

        self.im = self.ax.imshow(
            data.T,
            origin="lower",
            extent=(*get_extent(data, self.spatial_dims[0]), *get_extent(data, self.spatial_dims[1])),
            norm=self.dep_scale,
        )

        self.fig.colorbar(self.im)
        data_lower, data_upper = self._get_var_bounds()
        plt_util.update_cbar(self.im, data_min_override=data_lower, data_max_override=data_upper)

        plt_util.update_title(self.ax, self.source.get_modified_var_name(), DIMENSIONS[self.time_dim].get_coordinate_label(data[self.time_dim]))

        self.ax.set_aspect(1 / self.ax.get_data_ratio())
        self.ax.set_xlabel(DIMENSIONS[self.spatial_dims[0]].to_axis_label())
        self.ax.set_ylabel(DIMENSIONS[self.spatial_dims[1]].to_axis_label())

        self.fig.tight_layout()

    def _update_fig(self, frame: int):
        data = self._get_data_at_frame(frame)

        self.im.set_array(data.T)

        plt_util.update_title(self.ax, self.source.get_modified_var_name(), DIMENSIONS[self.time_dim].get_coordinate_label(data[self.time_dim]))
        return [self.im, self.ax.title]


class FieldAnimation2dPolar(FieldAnimation):
    ax: PolarAxes

    def __init__(
        self,
        steps: list[int],
        source: FieldSource,
        time_dim: str,
        spatial_dims: tuple[str, str],
    ):
        super().__init__(steps, source, time_dim, subplot_kw={"projection": "polar"})

        self.spatial_dims = spatial_dims

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

        plt_util.update_title(self.ax, self.source.get_modified_var_name(), DIMENSIONS[self.time_dim].get_coordinate_label(data[self.time_dim]))

        # FIXME make the labels work
        # self.ax.set_xlabel(DIMENSIONS[self.dims[1]].to_axis_label())
        # self.ax.set_ylabel(DIMENSIONS[self.dims[0]].to_axis_label())

        self.fig.tight_layout()

    def _update_fig(self, frame: int):
        data = self._get_data_at_frame(frame)

        self.im.set_array(data)

        plt_util.update_title(self.ax, self.source.get_modified_var_name(), DIMENSIONS[self.time_dim].get_coordinate_label(data[self.time_dim]))
        return [self.im, self.ax.title]


class FieldAnimation1d(FieldAnimation):
    def __init__(
        self,
        steps: list[int],
        source: FieldSource,
        time_dim: str,
        spatial_dim: str,
    ):
        super().__init__(steps, source, time_dim)

        self.dim = spatial_dim
        self.fits: list[Fit] = []
        self.show_t0 = False

    def _init_fig(self):
        data = self._get_data_at_frame(0)
        xdata = data.coords[data.dims[0]]

        if self.show_t0:
            self.ax.plot(xdata, data, "-", label=DIMENSIONS[self.time_dim].get_coordinate_label(self.data.coords[self.time_dim][0]))

        line_type = "." if self.fits else "-"
        [self.line] = self.ax.plot(xdata, data, line_type)

        plt_util.update_title(self.ax, self.source.get_modified_var_name(), DIMENSIONS[self.time_dim].get_coordinate_label(data[self.time_dim]))
        self._update_ybounds()
        self.ax.set_xlabel(DIMENSIONS[self.dim].to_axis_label())
        self.ax.set_ylabel(f"${self.source.get_modified_var_name()}$")

        self.ax.set_xscale(self.indep_scale)
        self.ax.set_yscale(self.dep_scale)

        self.fit_lines = [fit.plot_fit(self.ax, data) for fit in self.fits]

        if self.fits or self.show_t0:
            self.ax.legend()

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

        plt_util.update_title(self.ax, self.source.get_modified_var_name(), DIMENSIONS[self.time_dim].get_coordinate_label(data[self.time_dim]))
        return [self.line, self.ax.yaxis, self.ax.title]

    def _update_ybounds(self):
        ymin, ymax = plt_util.symmetrize_bounds(*self._get_var_bounds())
        self.ax.set_ybound(ymin, ymax)

    def add_fits(self, fits: list[Fit]):
        self.fits.extend(fits)
