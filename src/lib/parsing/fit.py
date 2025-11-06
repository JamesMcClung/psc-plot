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
        # TODO actually do a fit
        fit_da = self._get_fit_data(da)
        [fit_line] = ax.plot(fit_da.coords[fit_da.dims[0]], fit_da, "o", label="hi")
        return fit_line

    def update_fit(self, da: xr.DataArray, line: Line2D):
        fit_da = self._get_fit_data(da)
        line.set_data(fit_da.coords[fit_da.dims[0]], fit_da)

    def _get_fit_data(self, da: xr.DataArray) -> xr.DataArray:
        slicer = PosSlice(da.dims[0], self.min_x, self.max_x)
        da = slicer.apply(da)
        return da
