from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import xarray as xr
from matplotlib.projections.polar import PolarAxes

from lib.data.data_with_attrs import Field
from lib.dimension import DIMENSIONS
from lib.plotting import plt_util
from lib.plotting.animated_plot import AnimatedPlot
from lib.plotting.frame_data_traits import (
    HasAxes,
    HasColorNorm,
    HasFieldData,
    HasLineType,
    HasSpatialScales,
)


class AnimatedFieldPlot(AnimatedPlot[Field]):
    def _get_nframes(self) -> int:
        return len(self.data.coordss[self.time_dim])

    def _get_var_bounds(self) -> tuple[float, float]:
        bounds = np.nanquantile(self.data.data, [0, 1])
        return bounds


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
        da = data.data

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

        plt_util.update_title(self.ax, data.metadata.var_latex, [DIMENSIONS[dim].get_coordinate_label(pos) for dim, pos in data.coordss.items() if pos.shape == ()])

        self.ax.set_aspect(1 / self.ax.get_data_ratio())
        self.ax.set_xlabel(DIMENSIONS[self.spatial_dims[0]].to_axis_label())
        self.ax.set_ylabel(DIMENSIONS[self.spatial_dims[1]].to_axis_label())

        self.post_init_fig(init_data)
        self.fig.tight_layout()

    def _update_fig(self, frame: int):
        data = self._get_data_at_frame(frame)

        update_data = self.UpdateData(data=data)
        self.pre_update_fig(update_data)

        self.im.set_data(data.data)

        plt_util.update_title(self.ax, data.metadata.var_latex, [DIMENSIONS[dim].get_coordinate_label(pos) for dim, pos in data.coordss.items() if pos.shape == ()])

        self.post_update_fig(update_data)
        return [self.im, self.ax.title]

    def _get_data_at_frame(self, frame: int) -> Field:
        data = super()._get_data_at_frame(frame)
        return data.assign_data(data.data.transpose(*reversed(self.spatial_dims)))


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

        vertices_theta = np.concat((data.coordss[self.spatial_dims[1]].data, [2 * np.pi]))
        vertices_theta -= vertices_theta[1] / 2
        vertices_r = list(data.coordss[self.spatial_dims[0]].data)
        vertices_r += [vertices_r[-1] + vertices_r[1]]

        self.im = self.ax.pcolormesh(
            *np.meshgrid(vertices_theta, vertices_r),
            data,
            shading="flat",
            norm=init_data.color_norm,
        )

        self.fig.colorbar(self.im)
        data_lower, data_upper = self._get_var_bounds()
        plt_util.update_cbar(self.im, data_min_override=data_lower, data_max_override=data_upper)

        plt_util.update_title(self.ax, data.metadata.var_latex, [DIMENSIONS[dim].get_coordinate_label(pos) for dim, pos in data.coordss.items() if pos.shape == ()])

        # FIXME make the labels work
        # self.ax.set_xlabel(DIMENSIONS[self.dims[1]].to_axis_label())
        # self.ax.set_ylabel(DIMENSIONS[self.dims[0]].to_axis_label())

        self.post_init_fig(init_data)
        self.fig.tight_layout()

    def _update_fig(self, frame: int):
        data = self._get_data_at_frame(frame)

        update_data = self.UpdateData(data=data)
        self.pre_update_fig(update_data)

        self.im.set_array(data)

        plt_util.update_title(self.ax, data.metadata.var_latex, [DIMENSIONS[dim].get_coordinate_label(pos) for dim, pos in data.coordss.items() if pos.shape == ()])

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
        ydata = data.data

        init_data = self.InitData(
            data=data,
            axes=self.ax,
            line_type="-",
            spatial_scales=["linear", "linear"],
            last_spatial_dim_is_dependent=True,
        )

        self.pre_init_fig(init_data)

        [self.line] = self.ax.plot(xdata, ydata, init_data.line_type)

        plt_util.update_title(self.ax, data.metadata.var_latex, [DIMENSIONS[dim].get_coordinate_label(pos) for dim, pos in data.coordss.items() if pos.shape == ()])
        self.ax.set_xlabel(DIMENSIONS[self.spatial_dims[0]].to_axis_label())
        self.ax.set_ylabel(f"${data.metadata.var_latex}$")

        self.ax.set_xscale(init_data.spatial_scales[0])
        self.ax.set_yscale(init_data.spatial_scales[1])

        self._update_ybounds()

        self.post_init_fig(init_data)

        self.fig.tight_layout()

    def _update_fig(self, frame: int):
        data = self._get_data_at_frame(frame)
        ydata = data.data

        update_data = self.UpdateData(data=data, axes=self.ax)

        self.pre_update_fig(update_data)

        self.line.set_ydata(ydata)

        plt_util.update_title(self.ax, data.metadata.var_latex, [DIMENSIONS[dim].get_coordinate_label(pos) for dim, pos in data.coordss.items() if pos.shape == ()])

        self.post_update_fig(update_data)

        return [self.line, self.ax.yaxis, self.ax.title]

    def _update_ybounds(self):
        ymin, ymax = plt_util.symmetrize_bounds(*self._get_var_bounds())
        self.ax.set_ybound(ymin, ymax)
