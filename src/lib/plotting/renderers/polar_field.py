from dataclasses import dataclass
from typing import Any

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from lib.data.data_with_attrs import Field
from lib.plotting import plt_util
from lib.plotting.frame_data_traits import HasAxes, HasColorNorm, HasFieldData, HasSpatialScales
from lib.plotting.plot_info import PlotInfo, PolarMeshInfo
from lib.plotting.renderer import Renderer
from lib.scale import LinearScale


class PolarFieldRenderer(Renderer[Field]):
    @dataclass(kw_only=True)
    class InitData(HasFieldData, HasSpatialScales, HasColorNorm, HasAxes): ...

    @dataclass(kw_only=True)
    class UpdateData(HasFieldData, HasAxes): ...

    def subplot_kw(self) -> dict[str, Any]:
        return {"projection": "polar"}

    def make_init_data(self, fig: Figure, ax: Axes, frame_data: Field) -> InitData:
        return self.InitData(
            data=frame_data,
            spatial_scales=[LinearScale(), LinearScale()],
            color_norm=LinearScale(),
            color_is_dependent=True,
            axes=ax,
        )

    def init(self, fig: Figure, ax: Axes, full_data: Field, frame_data: Field, init_data: InitData) -> None:
        spatial_dims = frame_data.metadata.spatial_dims

        # must set scale before making image
        ax.set_rscale(init_data.spatial_scales[0])

        vertices_theta = frame_data.coordss[spatial_dims[1]]
        vertices_theta = np.concat([vertices_theta, [vertices_theta[-1] + vertices_theta[1] - vertices_theta[0]]])
        vertices_r = list(frame_data.coordss[spatial_dims[0]])
        vertices_r = np.concat([vertices_r, [vertices_r[-1] + vertices_r[1] - vertices_r[0]]])

        if vertices_theta[0] == 0.0:
            # FIXME hacky check for interpolated values
            # there are two different ways to go from cartesian to polar:
            # - interpolating onto a polar grid, in which case theta coords are "cell centered" (and happen to start at 0)
            # - scattering and binning, in which case theta coords are "node centered" (and happen to start at -pi)
            # this does a half-cell rotation in the former case to transform to "node centered" coords, which matlotlib expects
            vertices_theta -= vertices_theta[1] / 2.0

        self.im = ax.pcolormesh(
            *np.meshgrid(vertices_theta, vertices_r),
            frame_data.active_data,
            shading="flat",
            norm=init_data.color_norm,
        )

        fig.colorbar(self.im)
        data_lower, data_upper = full_data.var_bounds
        plt_util.update_cbar(self.im, data_min_override=data_lower, data_max_override=data_upper)

        plt_util.update_title(ax, frame_data.metadata, [frame_data.metadata.var_infos[dim].get_coordinate_label(pos) for dim, pos in frame_data.coordss.items() if pos.shape == ()])

        # FIXME make the labels work
        # ax.set_xlabel(frame_data.metadata.var_info[spatial_dims[1]].to_axis_label())
        # ax.set_ylabel(frame_data.metadata.var_info[spatial_dims[0]].to_axis_label())

    def make_update_data(self, ax: Axes, frame_data: Field) -> UpdateData:
        return self.UpdateData(data=frame_data, axes=ax)

    def draw(self, ax: Axes, frame_data: Field, update_data: UpdateData) -> None:
        self.im.set_array(frame_data.active_data)

        plt_util.update_title(ax, frame_data.metadata, [frame_data.metadata.var_infos[dim].get_coordinate_label(pos) for dim, pos in frame_data.coordss.items() if pos.shape == ()])

    def init_plot_info(self, full_data: Field, frame_data: Field) -> PlotInfo:
        [r_dim, theta_dim] = frame_data.metadata.spatial_dims
        color_dim = frame_data.metadata.active_key

        theta_vertices = frame_data.coordss[theta_dim]
        theta_vertices = np.concat([theta_vertices, [theta_vertices[-1] + theta_vertices[1] - theta_vertices[0]]])
        r_vertices = list(frame_data.coordss[r_dim])
        r_vertices = np.concat([r_vertices, [r_vertices[-1] + r_vertices[1] - r_vertices[0]]])
        if theta_vertices[0] == 0.0:
            # FIXME hacky check for interpolated values
            # there are two different ways to go from cartesian to polar:
            # - interpolating onto a polar grid, in which case theta coords are "cell centered" (and happen to start at 0)
            # - scattering and binning, in which case theta coords are "node centered" (and happen to start at -pi)
            # this does a half-cell rotation in the former case to transform to "node centered" coords, which matlotlib expects
            theta_vertices -= theta_vertices[1] / 2.0

        self.plot_info = PolarMeshInfo(
            data=frame_data.active_data,
            r_dim=r_dim,
            theta_dim=theta_dim,
            color_dim=color_dim,
            r_vertices=r_vertices,
            theta_vertices=theta_vertices,
            subject=frame_data.metadata.active_var_info.to_axis_label(),
            dim_scales={
                r_dim: frame_data.metadata.var_infos[r_dim].scale,
                color_dim: frame_data.metadata.var_infos[color_dim].scale,
            },
            dim_bounds={
                color_dim: full_data.var_bounds,
            },
            dim_displays={
                r_dim: frame_data.metadata.var_infos[r_dim].display,
                theta_dim: frame_data.metadata.var_infos[theta_dim].display,
                color_dim: None,
            },
            dim_units={
                r_dim: frame_data.metadata.var_infos[r_dim].unit,
                theta_dim: frame_data.metadata.var_infos[theta_dim].unit,
                color_dim: frame_data.metadata.var_infos[color_dim].unit,
            },
        )

        for dim, coord in frame_data.coordss.items():
            if coord.shape == ():
                self.plot_info.scalar_coord_values[dim] = coord
                self.plot_info.dim_displays[dim] = frame_data.metadata.var_infos[dim].display
                self.plot_info.dim_units[dim] = frame_data.metadata.var_infos[dim].unit

        return self.plot_info

    def update_plot_info(self, frame_data: Field, update_data: UpdateData):
        self.plot_info.set("data", frame_data.active_data)
        self.plot_info.set("scalar_coord_values", {dim: coord for dim, coord in frame_data.coordss.items() if coord.shape == ()})
