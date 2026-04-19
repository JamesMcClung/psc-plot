from lib.data.data_with_attrs import DataWithAttrs, Field, List
from lib.plotting.animated_plot import AnimatedPlot
from lib.plotting.plot import Plot
from lib.plotting.renderer import Renderer
from lib.plotting.renderers.field_1d import Field1dRenderer
from lib.plotting.renderers.field_2d import Field2dRenderer
from lib.plotting.renderers.polar_field import PolarFieldRenderer
from lib.plotting.renderers.scatter import ScatterRenderer
from lib.plotting.static_plot import StaticPlot


def _get_renderer(data: DataWithAttrs) -> Renderer:
    spatial_dims = data.metadata.spatial_dims

    if isinstance(data, Field):
        if len(spatial_dims) == 1:
            return Field1dRenderer()
        elif len(spatial_dims) == 2:
            if data.metadata.dims[spatial_dims[0]].geometry == "polar:r" and data.metadata.dims[spatial_dims[1]].geometry == "polar:theta":
                return PolarFieldRenderer()
            return Field2dRenderer()
        else:
            raise NotImplementedError("don't have 3D field plots yet")

    elif isinstance(data, List):
        if len(spatial_dims) == 1:
            return ScatterRenderer()
        else:
            raise NotImplementedError("don't have 2D or 3D scatter plots yet")

    raise TypeError(f"unexpected data type: {type(data)}")


def get_plot(data: DataWithAttrs) -> Plot:
    renderer = _get_renderer(data)

    if data.metadata.time_dim:
        return AnimatedPlot(renderer, data)
    else:
        return StaticPlot(renderer, data)
