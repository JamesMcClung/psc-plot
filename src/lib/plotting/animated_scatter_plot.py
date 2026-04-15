import typing
from dataclasses import dataclass

import numpy as np

from lib.data.data_with_attrs import FullList
from lib.dimension import DIM_DEFAULTS
from lib.plotting import plt_util
from lib.plotting.animated_plot import AnimatedPlot
from lib.plotting.frame_data_traits import (
    HasAxes,
    HasColorNorm,
    HasFullListData,
    HasSpatialScales,
)
from lib.plotting.plt_util import get_axis_label


class AnimatedScatterPlot(AnimatedPlot[FullList]):
    @dataclass(kw_only=True)
    class InitData(HasFullListData, HasAxes, HasSpatialScales, HasColorNorm): ...

    @dataclass(kw_only=True)
    class UpdateData(HasFullListData, HasAxes): ...

    def __init__(
        self,
        data: FullList,
        *,
        subplot_kw: dict[str, typing.Any] = {},
    ):
        super().__init__(data, subplot_kw=subplot_kw)

        self.dependent_var = data.metadata.dependent_var

    def _init_fig(self):
        data = self._get_data_at_frame(0)
        df = data.data

        init_data = self.InitData(
            data=data,
            axes=self.ax,
            spatial_scales=["linear", "linear"],
            last_spatial_dim_is_dependent=True,
            color_norm="linear",
        )

        self.pre_init_fig(init_data)

        self.ax.set_xscale(init_data.spatial_scales[0])
        self.ax.set_yscale(init_data.spatial_scales[1])

        self.ax.set_xlabel(get_axis_label(self.spatial_dims[0], data.metadata))
        self.ax.set_ylabel(plt_util.format_label(data.metadata) if self.dependent_var == data.metadata.var_name else get_axis_label(self.dependent_var, data.metadata))

        self.ax.set_xlim(*self.data.bounds(self.spatial_dims[0]))
        self.ax.set_ylim(*self.data.bounds(self.dependent_var))

        if data.metadata.color_dim:
            self.scatter = self.ax.scatter(
                df[self.spatial_dims[0]],
                df[self.dependent_var],
                c=df[data.metadata.color_dim],
                norm=init_data.color_norm,
                s=1,
            )

            self.fig.colorbar(self.scatter, label=get_axis_label(data.metadata.color_dim, data.metadata))
            data_lower, data_upper = self.data.bounds(data.metadata.color_dim)
            plt_util.update_cbar(self.scatter, data_min_override=data_lower, data_max_override=data_upper)
        else:
            self.scatter = self.ax.scatter(
                df[self.spatial_dims[0]],
                df[self.dependent_var],
                color=self.ax._get_lines.get_next_color(),  # scatter() uses a different color cycler than plot(); this uses the plot() cycler manually
                s=0.5,
            )

        plt_util.update_title(self.ax, data.metadata, [DIM_DEFAULTS[dim].get_coordinate_label(pos) for dim, pos in data.coordss.items() if isinstance(pos, float)])

        self.ax.set_aspect(1 / self.ax.get_data_ratio())

        self.post_init_fig(init_data)

        self.fig.tight_layout()

    def _update_fig(self, frame: int):
        data = self._get_data_at_frame(frame)
        df = data.data

        update_data = self.UpdateData(data=data, axes=self.ax)

        self.pre_update_fig(update_data)

        self.scatter.set_offsets(np.array([df[self.spatial_dims[0]], df[self.dependent_var]]).T)
        plt_util.update_title(self.ax, data.metadata, [DIM_DEFAULTS[dim].get_coordinate_label(pos) for dim, pos in data.coordss.items() if isinstance(pos, float)])

        if data.metadata.color_dim:
            self.scatter.set_array(df[data.metadata.color_dim])

        self.post_update_fig(update_data)

        return [self.scatter, self.ax.title]
