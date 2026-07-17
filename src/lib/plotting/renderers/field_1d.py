from dataclasses import dataclass

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from lib.data.data_with_attrs import Field
from lib.plotting import plt_util
from lib.plotting.frame_data_traits import (
    HasAxes,
    HasFieldData,
    HasLineType,
)
from lib.plotting.plot_info import LineInfo, PlotInfo
from lib.plotting.renderer import Renderer


class Field1dRenderer(Renderer[Field]):
    @dataclass(kw_only=True)
    class InitData(HasFieldData, HasLineType, HasAxes): ...

    def make_init_data(self, fig: Figure, ax: Axes, frame_data: Field) -> InitData:
        return self.InitData(
            data=frame_data,
            axes=ax,
            line_type="-",
        )

    def init_plot_info(self) -> PlotInfo:
        full_data = self.full_data
        frame_data = self._get_data_at_frame(0)

        [x_dim] = frame_data.metadata.spatial_dims
        y_dim = frame_data.metadata.active_key

        self.plot_info = LineInfo(
            x_data=frame_data.coordss[x_dim],
            y_data=frame_data.active_data,
            x_dim=x_dim,
            y_dim=y_dim,
            subject=frame_data.metadata.active_var_info.to_axis_label(),
            dim_scales={
                x_dim: frame_data.metadata.var_infos[x_dim].scale,
                y_dim: frame_data.metadata.var_infos[y_dim].scale,
            },
            dim_bounds={
                x_dim: (frame_data.coordss[x_dim][0], frame_data.coordss[x_dim][-1]),
                y_dim: plt_util.symmetrize_bounds(*full_data.var_bounds),
            },
            dim_displays={
                x_dim: frame_data.metadata.var_infos[x_dim].display,
                y_dim: frame_data.metadata.var_infos[y_dim].display,
            },
            dim_units={
                x_dim: frame_data.metadata.var_infos[x_dim].unit,
                y_dim: frame_data.metadata.var_infos[y_dim].unit,
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

        self.plot_info.set("y_data", frame_data.active_data)
        self.plot_info.set("scalar_coord_values", {dim: coord for dim, coord in frame_data.coordss.items() if coord.shape == ()})
