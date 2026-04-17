from dataclasses import dataclass

import numpy as np

from lib.data.data_with_attrs import Field
from lib.plotting import plt_util
from lib.plotting.frame_data_traits import (
    HasAxes,
    HasFieldData,
    HasLineType,
    HasSpatialScales,
)
from lib.plotting.plt_util import get_axis_label
from lib.plotting.static_plot import StaticPlot


class StaticFieldPlot(StaticPlot[Field]):
    def _get_var_bounds(self) -> tuple[float, float]:
        bounds = np.nanquantile(self.data.active_data, [0, 1])
        return bounds


class Static1dFieldPlot(StaticFieldPlot):
    @dataclass(kw_only=True)
    class InitData(HasFieldData, HasAxes, HasSpatialScales, HasLineType): ...

    def _init_fig(self):
        data = self.data
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

        ymin, ymax = plt_util.symmetrize_bounds(*self._get_var_bounds())
        self.ax.set_ybound(ymin, ymax)

        self.post_init_fig(init_data)
        self.fig.tight_layout()
