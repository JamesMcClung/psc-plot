import numpy as np
import xarray as xr

from lib.data.keys import VAR_LATEX_KEY
from lib.dimension import DIMENSIONS
from lib.plotting import plt_util
from lib.plotting.static_plot import StaticPlot


class StaticFieldPlot(StaticPlot[xr.DataArray]):
    def _get_var_bounds(self) -> tuple[float, float]:
        bounds = np.nanquantile(self.data, [0, 1])
        return bounds


class Static1dFieldPlot(StaticFieldPlot):
    def __init__(
        self,
        data: xr.DataArray,
        *,
        scales: list[plt_util.Scale] = [],
    ):
        super().__init__(data, scales=scales)

    def _init_fig(self):
        data = self.data
        xdata = data.coords[data.dims[0]]

        line_type = "-"

        [self.line] = self.ax.plot(xdata, data, line_type)

        plt_util.update_title(self.ax, data.attrs[VAR_LATEX_KEY], [DIMENSIONS[dim].get_coordinate_label(pos) for dim, pos in data.coords.items() if pos.shape == ()])
        self.ax.set_xlabel(DIMENSIONS[self.spatial_dims[0]].to_axis_label())
        self.ax.set_ylabel(f"${data.attrs[VAR_LATEX_KEY]}$")

        self.ax.set_xscale(self.scales[1])
        self.ax.set_yscale(self.scales[0])

        ymin, ymax = plt_util.symmetrize_bounds(*self._get_var_bounds())
        self.ax.set_ybound(ymin, ymax)

        self.fig.tight_layout()
