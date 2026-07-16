from dataclasses import dataclass

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from lib.data.data_with_attrs import Field
from lib.plotting import plt_util
from lib.plotting.frame_data_traits import (
    HasAxes,
    HasFieldData,
    HasLineType,
    HasSpatialScales,
)
from lib.plotting.plot_info import LineInfo, PlotInfo
from lib.plotting.renderer import Renderer
from lib.scale import LinearScale


class Field1dRenderer(Renderer[Field]):
    @dataclass(kw_only=True)
    class InitData(HasFieldData, HasLineType, HasAxes, HasSpatialScales): ...

    @dataclass(kw_only=True)
    class UpdateData(HasFieldData, HasAxes): ...

    def make_init_data(self, fig: Figure, ax: Axes, frame_data: Field) -> InitData:
        return self.InitData(
            data=frame_data,
            axes=ax,
            line_type="-",
            spatial_scales=[LinearScale(), LinearScale()],
            last_spatial_dim_is_dependent=True,
        )

    def init(self, fig: Figure, ax: Axes, full_data: Field, frame_data: Field, init_data: InitData) -> None:
        [dim_x] = frame_data.metadata.spatial_dims
        xdata = frame_data.coordss[dim_x]
        ydata = frame_data.active_data

        [self.line] = ax.plot(xdata, ydata, init_data.line_type)

        plt_util.update_title(ax, frame_data.metadata, [frame_data.metadata.var_infos[dim].get_coordinate_label(pos) for dim, pos in frame_data.coordss.items() if pos.shape == ()])
        ax.set_xlabel(frame_data.metadata.var_infos[dim_x].to_axis_label())
        ax.set_ylabel(frame_data.metadata.active_var_info.to_axis_label())

        ax.set_xscale(init_data.spatial_scales[0])
        ax.set_yscale(init_data.spatial_scales[1])

        ymin, ymax = plt_util.symmetrize_bounds(*full_data.var_bounds)
        ax.set_ybound(ymin, ymax)

    def make_update_data(self, ax: Axes, frame_data: Field) -> UpdateData:
        return self.UpdateData(data=frame_data, axes=ax)

    def draw(self, ax: Axes, frame_data: Field, update_data: UpdateData) -> None:
        self.line.set_ydata(frame_data.active_data)

        plt_util.update_title(ax, frame_data.metadata, [frame_data.metadata.var_infos[dim].get_coordinate_label(pos) for dim, pos in frame_data.coordss.items() if pos.shape == ()])

    def init_plot_info(self, full_data: Field, frame_data: Field, init_data: InitData) -> PlotInfo:
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

    def update_plot_info(self, frame_data: Field, update_data: UpdateData):
        self.plot_info.set("y_data", frame_data.active_data)
        self.plot_info.set("scalar_coord_values", {dim: coord for dim, coord in frame_data.coordss.items() if coord.shape == ()})
