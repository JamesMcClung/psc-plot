from __future__ import annotations

from dataclasses import dataclass

import dask
import numpy as np
import xarray as xr
from matplotlib.projections.polar import PolarAxes

from lib.data.data_with_attrs import Field
from lib.plotting import plt_util
from lib.plotting.animated_plot import AnimatedPlot
from lib.plotting.frame_data_traits import (
    HasAxes,
    HasColorNorm,
    HasFieldData,
    HasLineType,
    HasSpatialScales,
)
from lib.plotting.plt_util import get_axis_label


class AnimatedFieldPlot(AnimatedPlot[Field]):
    def _get_var_bounds(self) -> tuple[float, float]:
        data = self.data.active_data
        return dask.compute(
            np.min(data),
            np.max(data),
        )


def get_extent(da: xr.DataArray, dim: str) -> tuple[float, float]:
    lower = da[dim][0]
    upper = da[dim][-1] + (da[dim][1] - da[dim][0])
    return (float(lower), float(upper))


class Animated2dFieldPlot(AnimatedFieldPlot):
    @dataclass(kw_only=True)
    class InitData(HasFieldData, HasSpatialScales, HasColorNorm): ...

    @dataclass(kw_only=True)
    class UpdateData(HasFieldData): ...

    def _init_fig(self):
        data = self._get_data_at_frame(0)
        da = data.active_data

        init_data = self.InitData(
            data=data,
            spatial_scales=["linear", "linear"],
            color_norm="linear",
            color_is_dependent=True,
        )
        self.pre_init_fig(init_data)

        # must set scale (log, linear) before making image
        self.ax.set_xscale(init_data.spatial_scales[0])
        self.ax.set_yscale(init_data.spatial_scales[1])

        self.im = self.ax.imshow(
            da,
            origin="lower",
            extent=(*get_extent(da, self.spatial_dims[0]), *get_extent(da, self.spatial_dims[1])),
            norm=init_data.color_norm,
        )

        self.fig.colorbar(self.im)
        data_lower, data_upper = self._get_var_bounds()
        plt_util.update_cbar(self.im, data_min_override=data_lower, data_max_override=data_upper)

        plt_util.update_title(self.ax, data.metadata, [plt_util.get_dim(dim, data.metadata).get_coordinate_label(pos) for dim, pos in data.coordss.items() if pos.shape == ()])

        self.ax.set_aspect(1 / self.ax.get_data_ratio())
        self.ax.set_xlabel(get_axis_label(self.spatial_dims[0], data.metadata))
        self.ax.set_ylabel(get_axis_label(self.spatial_dims[1], data.metadata))

        self.post_init_fig(init_data)
        self.fig.tight_layout()

    def _update_fig(self, frame: int):
        data = self._get_data_at_frame(frame)

        update_data = self.UpdateData(data=data)
        self.pre_update_fig(update_data)

        self.im.set_data(data.active_data)

        plt_util.update_title(self.ax, data.metadata, [plt_util.get_dim(dim, data.metadata).get_coordinate_label(pos) for dim, pos in data.coordss.items() if pos.shape == ()])

        self.post_update_fig(update_data)
        return [self.im, self.ax.title]

    def _get_data_at_frame(self, frame: int) -> Field:
        data = super()._get_data_at_frame(frame)
        return data.with_active_data(data.active_data.transpose(*reversed(self.spatial_dims)))


class AnimatedPolarFieldPlot(AnimatedFieldPlot):
    ax: PolarAxes

    def __init__(
        self,
        data: Field,
    ):
        super().__init__(data, subplot_kw={"projection": "polar"})

    @dataclass(kw_only=True)
    class InitData(HasFieldData, HasSpatialScales, HasColorNorm): ...

    @dataclass(kw_only=True)
    class UpdateData(HasFieldData): ...

    def _init_fig(self):
        data = self._get_data_at_frame(0)

        init_data = self.InitData(
            data=data,
            spatial_scales=["linear", "linear"],
            color_norm="linear",
            color_is_dependent=True,
        )
        self.pre_init_fig(init_data)

        # must set scale before making image
        self.ax.set_rscale(init_data.spatial_scales[0])

        vertices_theta = data.coordss[self.spatial_dims[1]]
        vertices_theta = np.concat([vertices_theta, [vertices_theta[-1] + vertices_theta[1] - vertices_theta[0]]])
        vertices_r = list(data.coordss[self.spatial_dims[0]])
        vertices_r = np.concat([vertices_r, [vertices_r[-1] + vertices_r[1] - vertices_r[0]]])

        if vertices_theta[0] == 0.0:
            # FIXME hacky check for interpolated values
            # there are two different ways to go from cartesian to polar:
            # - interpolating onto a polar grid, in which case theta coords are "cell centered" (and happen to start at 0)
            # - scattering and binning, in which case theta coords are "node centered" (and happen to start at -pi)
            # this does a half-cell rotation in the former case to transform to "node centered" coords, which matlotlib expects
            vertices_theta -= vertices_theta[1] / 2.0

        self.im = self.ax.pcolormesh(
            *np.meshgrid(vertices_theta, vertices_r),
            data.active_data,
            shading="flat",
            norm=init_data.color_norm,
        )

        self.fig.colorbar(self.im)
        data_lower, data_upper = self._get_var_bounds()
        plt_util.update_cbar(self.im, data_min_override=data_lower, data_max_override=data_upper)

        plt_util.update_title(self.ax, data.metadata, [plt_util.get_dim(dim, data.metadata).get_coordinate_label(pos) for dim, pos in data.coordss.items() if pos.shape == ()])

        # FIXME make the labels work
        # self.ax.set_xlabel(get_axis_label(self.dims[1], data.metadata))
        # self.ax.set_ylabel(get_axis_label(self.dims[0], data.metadata))

        self.post_init_fig(init_data)
        self.fig.tight_layout()

    def _update_fig(self, frame: int):
        data = self._get_data_at_frame(frame)

        update_data = self.UpdateData(data=data)
        self.pre_update_fig(update_data)

        self.im.set_array(data.active_data)

        plt_util.update_title(self.ax, data.metadata, [plt_util.get_dim(dim, data.metadata).get_coordinate_label(pos) for dim, pos in data.coordss.items() if pos.shape == ()])

        self.post_update_fig(update_data)
        return [self.im, self.ax.title]


class Animated1dFieldPlot(AnimatedFieldPlot):
    @dataclass(kw_only=True)
    class InitData(HasFieldData, HasLineType, HasAxes, HasSpatialScales): ...

    @dataclass(kw_only=True)
    class UpdateData(HasFieldData, HasAxes): ...

    def _init_fig(self):
        data = self._get_data_at_frame(0)
        xdata = data.coordss[data.dims[0]]
        ydata = data.active_data

        init_data = self.InitData(
            data=data,
            axes=self.ax,
            line_type="-",
            spatial_scales=["linear", "linear"],
            last_spatial_dim_is_dependent=True,
        )

        self.pre_init_fig(init_data)

        [self.line] = self.ax.plot(xdata, ydata, init_data.line_type)

        plt_util.update_title(self.ax, data.metadata, [plt_util.get_dim(dim, data.metadata).get_coordinate_label(pos) for dim, pos in data.coordss.items() if pos.shape == ()])
        self.ax.set_xlabel(get_axis_label(self.spatial_dims[0], data.metadata))
        self.ax.set_ylabel(plt_util.format_label(data.metadata))

        self.ax.set_xscale(init_data.spatial_scales[0])
        self.ax.set_yscale(init_data.spatial_scales[1])

        self._update_ybounds()

        self.post_init_fig(init_data)

        self.fig.tight_layout()

    def _update_fig(self, frame: int):
        data = self._get_data_at_frame(frame)
        ydata = data.active_data

        update_data = self.UpdateData(data=data, axes=self.ax)

        self.pre_update_fig(update_data)

        self.line.set_ydata(ydata)

        plt_util.update_title(self.ax, data.metadata, [plt_util.get_dim(dim, data.metadata).get_coordinate_label(pos) for dim, pos in data.coordss.items() if pos.shape == ()])

        self.post_update_fig(update_data)

        return [self.line, self.ax.yaxis, self.ax.title]

    def _update_ybounds(self):
        ymin, ymax = plt_util.symmetrize_bounds(*self._get_var_bounds())
        self.ax.set_ybound(ymin, ymax)
