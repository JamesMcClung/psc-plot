from dataclasses import dataclass

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from lib.data.data_with_attrs import Field
from lib.plotting.frame_data_traits import HasAxes, HasFieldData
from lib.plotting.plot_info import PlotInfo, PolarMeshInfo
from lib.plotting.renderer import Renderer


class PolarFieldRenderer(Renderer[Field]):
    @dataclass(kw_only=True)
    class InitData(HasFieldData, HasAxes): ...

    def make_init_data(self, fig: Figure, ax: Axes, frame_data: Field) -> InitData:
        return self.InitData(
            data=frame_data,
            axes=ax,
        )

    def init_plot_info(self) -> PlotInfo:
        full_data = self.full_data
        frame_data = self._get_data_at_frame(0)

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

    def update_plot_info(self, frame: int):
        frame_data = self._get_data_at_frame(frame)

        self.plot_info.set("data", frame_data.active_data)
        self.plot_info.set("scalar_coord_values", {dim: coord for dim, coord in frame_data.coordss.items() if coord.shape == ()})
