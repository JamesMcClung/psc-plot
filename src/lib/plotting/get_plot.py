from lib.data.data_with_attrs import DataWithAttrs, Field, FullList, LazyList
from lib.dimension import DIMENSIONS
from lib.plotting.animated_field_plot import (
    Animated1dFieldPlot,
    Animated2dFieldPlot,
    AnimatedPolarFieldPlot,
)
from lib.plotting.animated_scatter_plot import AnimatedScatterPlot
from lib.plotting.plot import Plot
from lib.plotting.static_field_plot import Static1dFieldPlot


def get_plot(data: DataWithAttrs, **plot_kwargs) -> Plot:
    spatial_dims = data.metadata.spatial_dims

    if not data.metadata.time_dim:
        if isinstance(data, Field) and len(spatial_dims) == 1:
            PlotType = Static1dFieldPlot
        else:
            raise Exception("non-animated 2d/scatter plots not supported yet")
    else:
        if isinstance(data, LazyList):
            data = data.compute()

        if isinstance(data, Field):
            if len(spatial_dims) == 1:
                PlotType = Animated1dFieldPlot
            elif len(spatial_dims) == 2:
                if DIMENSIONS[spatial_dims[0]].geometry == "polar:r" and DIMENSIONS[spatial_dims[1]].geometry == "polar:theta":
                    PlotType = AnimatedPolarFieldPlot
                else:
                    PlotType = Animated2dFieldPlot
            else:
                raise NotImplementedError("don't have 3D field animations yet")

        elif isinstance(data, FullList):
            if len(spatial_dims) == 1:
                PlotType = AnimatedScatterPlot
            else:
                raise NotImplementedError("don't have 2D or 3D scatter animations yet")

    return PlotType(data, **plot_kwargs)
