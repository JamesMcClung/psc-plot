import numpy as np
import scipy.stats as stats
import xarray as xr
from matplotlib.axes import Axes
from matplotlib.lines import Line2D

from ..adaptors.field_adaptors.pos_slice import PosSlice

# TODO make this a plot plugin (and make plot plugins a thing)


class Fit:
    def __init__(self, arg: str):
        # TODO proper error handling
        # TODO actually parse different options for fits

        [min_x, max_x] = arg.split(":")
        self.min_x = float(min_x)
        self.max_x = float(max_x)

    def plot_fit(self, ax: Axes, da: xr.DataArray) -> Line2D:
        fit_da, label = self._get_fit_data(da)
        [fit_line] = ax.plot(fit_da.coords[fit_da.dims[0]], fit_da, "--", label=label)
        return fit_line

    def update_fit(self, da: xr.DataArray, line: Line2D):
        fit_da, label = self._get_fit_data(da)
        line.set_data(fit_da.coords[fit_da.dims[0]], fit_da)
        line.set_label(label)

    def _get_fit_data(self, da: xr.DataArray) -> tuple[xr.DataArray, str]:
        slicer = PosSlice(da.dims[0], self.min_x, self.max_x)
        da = slicer.apply(da)

        x_log = np.log(da.coords[da.dims[0]])
        y_log = np.log(da)

        [slope, intercept, rvalue, *_] = stats.linregress(x_log, y_log)

        y_fit_log = x_log * slope + intercept
        y_fit = np.exp(y_fit_log)

        label = f"$\\gamma={slope:.3f}$ ($r^2={rvalue**2:.3f}$)"

        return y_fit, label
