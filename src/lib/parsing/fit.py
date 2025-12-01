import numpy as np
import pandas as pd
import scipy.stats as stats
import xarray as xr
from matplotlib.axes import Axes
from matplotlib.lines import Line2D

from lib.data.adaptors.particle_adaptors.slice import Slice
from lib.data.keys import DEPENDENT_VAR_KEY, SPATIAL_DIMS_KEY

from ..data.adaptors.field_adaptors.pos_slice import PosSlice

# TODO make this a plot plugin (and make plot plugins a thing)


class Fit:
    def __init__(self, arg: str):
        # TODO proper error handling
        # TODO actually parse different options for fits

        [min_x, max_x] = arg.split(":")
        self.min_x = float(min_x)
        self.max_x = float(max_x)

    def plot_fit(self, ax: Axes, data: xr.DataArray | pd.DataFrame) -> Line2D:
        fit_da, label = self._get_fit_data(data)
        [fit_line] = ax.plot(fit_da.coords[fit_da.dims[0]], fit_da, "--", label=label)
        return fit_line

    def update_fit(self, data: xr.DataArray | pd.DataFrame, line: Line2D):
        fit_da, label = self._get_fit_data(data)
        line.set_data(fit_da.coords[fit_da.dims[0]], fit_da)
        line.set_label(label)

    def _get_fit_data(self, data: xr.DataArray | pd.DataFrame) -> tuple[xr.DataArray, str]:
        x_data, y_data = self._get_xy_data(data)
        x_log = np.log(x_data)
        y_log = np.log(y_data)

        [slope, intercept, rvalue, *_] = stats.linregress(x_log, y_log)

        y_fit_log = x_log * slope + intercept
        y_fit = np.exp(y_fit_log)

        label = f"$\\gamma={-slope:.3f}$ ($r^2={rvalue**2:.3f}$)"

        return y_fit, label

    def _get_xy_data(self, data: xr.DataArray | pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        if isinstance(data, xr.DataArray):
            slicer = PosSlice(data.dims[0], self.min_x, self.max_x)
            data = slicer.apply(data)
            return (data.coords[data.dims[0]], data)
        elif isinstance(data, pd.DataFrame):
            slicer = Slice(DEPENDENT_VAR_KEY, self.min_x, self.max_x)
            data = slicer.apply(data)
            return (data[DEPENDENT_VAR_KEY], data[data.attrs[SPATIAL_DIMS_KEY][0]])
