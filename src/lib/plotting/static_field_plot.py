import numpy as np

from lib.data.data_with_attrs import Field
from lib.dimension import DIMENSIONS
from lib.plotting import plt_util
from lib.plotting.static_plot import StaticPlot


class StaticFieldPlot(StaticPlot[Field]):
    def _get_var_bounds(self) -> tuple[float, float]:
        bounds = np.nanquantile(self.data.data, [0, 1])
        return bounds


class Static1dFieldPlot(StaticFieldPlot):
    def __init__(
        self,
        data: Field,
        *,
        scales: list[plt_util.Scale] = [],
    ):
        super().__init__(data, scales=scales)

    def _init_fig(self):
        data = self.data
        xdata = data.coordss[data.dims[0]]
        ydata = data.data

        line_type = "-"

        [self.line] = self.ax.plot(xdata, ydata, line_type)

        plt_util.update_title(self.ax, data.metadata.var_latex, [DIMENSIONS[dim].get_coordinate_label(pos) for dim, pos in data.coordss.items() if pos.shape == ()])
        self.ax.set_xlabel(DIMENSIONS[self.spatial_dims[0]].to_axis_label())
        self.ax.set_ylabel(f"${data.metadata.var_latex}$")

        self.ax.set_xscale(self.scales[1])
        self.ax.set_yscale(self.scales[0])

        ymin, ymax = plt_util.symmetrize_bounds(*self._get_var_bounds())
        self.ax.set_ybound(ymin, ymax)

        self.fig.tight_layout()
