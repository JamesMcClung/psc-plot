import xarray as xr
from matplotlib.axes import Axes
from matplotlib.lines import Line2D

# TODO make this a plot plugin (and make plot plugins a thing)


class Fit:
    def __init__(self, arg: str):
        # TODO proper error handling
        # TODO actually parse different options for fits
        pass

    def plot_fit(self, ax: Axes, da: xr.DataArray) -> Line2D:
        # TODO actually do a fit
        [fit_line] = ax.plot(da.coords[da.dims[0]], da, "o", label="hi")
        return fit_line
