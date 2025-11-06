import xarray as xr
from matplotlib.axes import Axes

# TODO make this a plot plugin (and make plot plugins a thing)


class Fit:
    def __init__(self, arg: str):
        # TODO proper error handling
        # TODO actually parse different options for fits
        pass

    def plot_fit(self, ax: Axes, da: xr.DataArray):
        # TODO actually do a fit
        ax.plot(da.coords[da.dims[0]], da, "o")
