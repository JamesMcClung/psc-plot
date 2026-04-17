from lib.data.data_with_attrs import DataWithAttrs, Field, List
from lib.plotting import plt_util
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
        if isinstance(data, Field):
            if len(spatial_dims) == 1:
                PlotType = Animated1dFieldPlot
            elif len(spatial_dims) == 2:
                if plt_util.get_dim(spatial_dims[0], data.metadata).geometry == "polar:r" and plt_util.get_dim(spatial_dims[1], data.metadata).geometry == "polar:theta":
                    PlotType = AnimatedPolarFieldPlot
                else:
                    PlotType = Animated2dFieldPlot
            else:
                raise NotImplementedError("don't have 3D field animations yet")

        elif isinstance(data, List):
            if len(spatial_dims) == 1:
                PlotType = AnimatedScatterPlot
            else:
                raise NotImplementedError("don't have 2D or 3D scatter animations yet")

    return PlotType(data, **plot_kwargs)
