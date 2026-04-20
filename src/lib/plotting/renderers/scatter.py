from dataclasses import dataclass

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from lib.data.data_with_attrs import FullList
from lib.plotting import plt_util
from lib.plotting.frame_data_traits import (
    HasAxes,
    HasColorNorm,
    HasFullListData,
    HasSpatialScales,
)
from lib.plotting.renderer import Renderer


class ScatterRenderer(Renderer[FullList]):
    @dataclass(kw_only=True)
    class InitData(HasFullListData, HasAxes, HasSpatialScales, HasColorNorm): ...

    @dataclass(kw_only=True)
    class UpdateData(HasFullListData, HasAxes): ...

    def make_init_data(self, fig: Figure, ax: Axes, frame_data: FullList) -> InitData:
        return self.InitData(
            data=frame_data,
            axes=ax,
            spatial_scales=["linear", "linear"],
            last_spatial_dim_is_dependent=True,
            color_norm="linear",
        )

    def init(self, fig: Figure, ax: Axes, full_data: FullList, frame_data: FullList, init_data: InitData) -> None:
        [dim_x, dim_y] = frame_data.metadata.spatial_dims
        df = frame_data.data

        ax.set_xscale(init_data.spatial_scales[0])
        ax.set_yscale(init_data.spatial_scales[1])

        ax.set_xlabel(frame_data.metadata.get_var_info(dim_x).to_axis_label())
        # FIXME there should be a single source of truth for how to format a label
        ax.set_ylabel(frame_data.metadata.get_var_info(dim_y).to_axis_label() if dim_y in frame_data.metadata.var_info or dim_y in frame_data.metadata.dims else plt_util.format_label(frame_data.metadata))

        ax.set_xlim(*full_data.bounds(dim_x))
        ax.set_ylim(*full_data.bounds(dim_y))

        if frame_data.metadata.color_dim:
            self.scatter = ax.scatter(
                df[dim_x],
                df[dim_y],
                c=df[frame_data.metadata.color_dim],
                norm=init_data.color_norm,
                s=1,
            )

            fig.colorbar(self.scatter, label=frame_data.metadata.get_var_info(frame_data.metadata.color_dim).to_axis_label())
            data_lower, data_upper = full_data.bounds(frame_data.metadata.color_dim)
            plt_util.update_cbar(self.scatter, data_min_override=data_lower, data_max_override=data_upper)
        else:
            self.scatter = ax.scatter(
                df[dim_x],
                df[dim_y],
                color=ax._get_lines.get_next_color(),
                s=0.5,
            )

        plt_util.update_title(ax, frame_data.metadata, [frame_data.metadata.get_var_info(dim).get_coordinate_label(pos) for dim, pos in frame_data.coordss.items() if isinstance(pos, float)])

        ax.set_aspect(1 / ax.get_data_ratio())

    def make_update_data(self, ax: Axes, frame_data: FullList) -> UpdateData:
        return self.UpdateData(data=frame_data, axes=ax)

    def draw(self, ax: Axes, frame_data: FullList, update_data: UpdateData) -> None:
        spatial_dims = frame_data.metadata.spatial_dims
        df = frame_data.data

        self.scatter.set_offsets(np.array([df[spatial_dims[0]], df[spatial_dims[1]]]).T)
        plt_util.update_title(ax, frame_data.metadata, [frame_data.metadata.get_var_info(dim).get_coordinate_label(pos) for dim, pos in frame_data.coordss.items() if isinstance(pos, float)])

        if frame_data.metadata.color_dim:
            self.scatter.set_array(df[frame_data.metadata.color_dim])
