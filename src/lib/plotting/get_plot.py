import pandas as pd
import xarray as xr

from lib.data.keys import SPATIAL_DIMS_KEY, TIME_DIM_KEY
from lib.dimension import DIMENSIONS
from lib.plotting.animated_field_plot import (
    FieldAnimation1d,
    FieldAnimation2d,
    FieldAnimation2dPolar,
)
from lib.plotting.animated_scatter_plot import AnimatedScatterPlot
from lib.plotting.plot import Plot


def get_plot(data: xr.DataArray | pd.DataFrame, **plot_kwargs) -> Plot:
    if not data.attrs[TIME_DIM_KEY]:
        # TODO use an argparse exception type
        raise Exception("non-animated plots not supported yet")

    spatial_dims = data.attrs[SPATIAL_DIMS_KEY]

    if isinstance(data, xr.DataArray):
        if len(spatial_dims) == 1:
            PlotType = FieldAnimation1d
        elif len(spatial_dims) == 2:
            if DIMENSIONS[spatial_dims[0]].geometry == "polar:r" and DIMENSIONS[spatial_dims[1]].geometry == "polar:theta":
                PlotType = FieldAnimation2dPolar
            else:
                PlotType = FieldAnimation2d
        else:
            raise NotImplementedError("don't have 3D field animations yet")

    elif isinstance(data, pd.DataFrame):
        if len(spatial_dims) == 1:
            PlotType = AnimatedScatterPlot
        else:
            raise NotImplementedError("don't have 2D or 3D scatter animations yet")

    return PlotType(data, **plot_kwargs)
