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
from lib.plotting.renderer import Renderer


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
            spatial_scales=["linear", "linear"],
            last_spatial_dim_is_dependent=True,
        )

    def init(self, fig: Figure, ax: Axes, full_data: Field, frame_data: Field, init_data: InitData) -> None:
        spatial_dims = frame_data.metadata.spatial_dims
        xdata = frame_data.coordss[frame_data.dims[0]]
        ydata = frame_data.active_data

        [self.line] = ax.plot(xdata, ydata, init_data.line_type)

        plt_util.update_title(ax, frame_data.metadata, [frame_data.metadata.dims[dim].get_coordinate_label(pos) for dim, pos in frame_data.coordss.items() if pos.shape == ()])
        ax.set_xlabel(frame_data.metadata.dims[spatial_dims[0]].to_axis_label())
        ax.set_ylabel(plt_util.format_label(frame_data.metadata))

        ax.set_xscale(init_data.spatial_scales[0])
        ax.set_yscale(init_data.spatial_scales[1])

        ymin, ymax = plt_util.symmetrize_bounds(*full_data.var_bounds)
        ax.set_ybound(ymin, ymax)

    def make_update_data(self, ax: Axes, frame_data: Field) -> UpdateData:
        return self.UpdateData(data=frame_data, axes=ax)

    def draw(self, ax: Axes, frame_data: Field, update_data: UpdateData) -> None:
        self.line.set_ydata(frame_data.active_data)

        plt_util.update_title(ax, frame_data.metadata, [frame_data.metadata.dims[dim].get_coordinate_label(pos) for dim, pos in frame_data.coordss.items() if pos.shape == ()])
