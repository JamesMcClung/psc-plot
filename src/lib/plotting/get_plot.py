import dask.dataframe as df
import pandas as pd
import xarray as xr

from lib.data.data_with_attrs import DataWithAttrs
from lib.data.keys import SPATIAL_DIMS_KEY, TIME_DIM_KEY
from lib.dimension import DIMENSIONS
from lib.plotting.animated_field_plot import (
    Animated1dFieldPlot,
    Animated2dFieldPlot,
    AnimatedPolarFieldPlot,
)
from lib.plotting.animated_scatter_plot import AnimatedScatterPlot
from lib.plotting.plot import Plot


def get_plot(data: DataWithAttrs, **plot_kwargs) -> Plot:
    if not data.attrs[TIME_DIM_KEY]:
        # TODO use an argparse exception type
        raise Exception("non-animated plots not supported yet")

    spatial_dims = data.attrs[SPATIAL_DIMS_KEY]

    if isinstance(data, df.DataFrame):
        attrs_before = data.attrs
        data = data.compute()
        data.attrs = attrs_before

    if isinstance(data, xr.DataArray):
        if len(spatial_dims) == 1:
            PlotType = Animated1dFieldPlot
        elif len(spatial_dims) == 2:
            if DIMENSIONS[spatial_dims[0]].geometry == "polar:r" and DIMENSIONS[spatial_dims[1]].geometry == "polar:theta":
                PlotType = AnimatedPolarFieldPlot
            else:
                PlotType = Animated2dFieldPlot
        else:
            raise NotImplementedError("don't have 3D field animations yet")

    elif isinstance(data, pd.DataFrame):
        if len(spatial_dims) == 1:
            PlotType = AnimatedScatterPlot
        else:
            raise NotImplementedError("don't have 2D or 3D scatter animations yet")

    return PlotType(data, **plot_kwargs)
