import numpy as np
import pandas as pd
import scipy.stats as stats
import xarray as xr
from matplotlib.axes import Axes
from matplotlib.lines import Line2D

from lib.data.adaptors.field_adaptors.pos import Pos
from lib.data.data_with_attrs import DataWithAttrs, Field, List

# TODO make this a plot plugin (and make plot plugins a thing)


class Fit:
    def __init__(self, arg: str):
        # TODO proper error handling
        # TODO actually parse different options for fits

        [min_x, max_x] = arg.split(":")
        self.min_x = float(min_x)
        self.max_x = float(max_x)

    def plot_fit(self, ax: Axes, data: DataWithAttrs) -> Line2D:
        x_data, y_data = self._get_xy_data(data)
        fit_y_data, label = self._get_fit_y_data(x_data, y_data)
        [fit_line] = ax.plot(x_data, fit_y_data, "--", label=label)
        return fit_line

    def update_fit(self, data: DataWithAttrs, line: Line2D):
        x_data, y_data = self._get_xy_data(data)
        fit_y_data, label = self._get_fit_y_data(x_data, y_data)
        line.set_data(x_data, fit_y_data)
        line.set_label(label)

    def _get_fit_y_data(self, x_data: np.ndarray, y_data: np.ndarray) -> tuple[np.ndarray, str]:
        x_log = np.log(x_data)
        y_log = np.log(y_data)

        [slope, intercept, rvalue, *_] = stats.linregress(x_log, y_log)

        y_fit_log = x_log * slope + intercept
        y_fit = np.exp(y_fit_log)

        label = f"$\\gamma={-slope:.3f}$ ($r^2={rvalue**2:.3f}$)"

        return y_fit, label

    def _get_xy_data(self, data: DataWithAttrs) -> tuple[np.ndarray, np.ndarray]:
        spatial_dim = data.metadata.spatial_dims[0]
        slicer = Pos({spatial_dim: slice(self.min_x, self.max_x)})
        data = slicer.apply(data)
        if isinstance(data, Field):
            return (data.coordss[spatial_dim], data.data)
        elif isinstance(data, List):
            return (data.data[spatial_dim], data.data[data.metadata.dependent_var])
