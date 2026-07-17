from lib.data.data_with_attrs import Field, List
from lib.data.data_world import DataWorld
from lib.data.plot_target import SpatialDimsRTheta, SpatialDimsXY
from lib.plotting.animated_plot import AnimatedPlot
from lib.plotting.plot import Plot
from lib.plotting.renderer import Renderer
from lib.plotting.renderers.field_1d import Field1dRenderer
from lib.plotting.renderers.field_2d import Field2dRenderer
from lib.plotting.renderers.polar_field import PolarFieldRenderer
from lib.plotting.renderers.scatter import ScatterRenderer
from lib.plotting.static_plot import StaticPlot


def get_plot(world: DataWorld) -> Plot:
    renderer = get_renderers(world)[0]

    if renderer.plot_target.time_dim:
        return AnimatedPlot(renderer, renderer.full_data)
    else:
        return StaticPlot(renderer, renderer.full_data)


def get_renderers(world: DataWorld) -> list[Renderer]:
    renderers = []

    for target in world.plot_targets:
        data = world.datas[target.prefix]

        if isinstance(data, Field):
            if not target.color_dim:
                renderers.append(Field1dRenderer(data, target))
            elif isinstance(target.spatial_dims, SpatialDimsRTheta):
                renderers.append(PolarFieldRenderer(data, target))
            elif isinstance(target.spatial_dims, SpatialDimsXY):
                renderers.append(Field2dRenderer(data, target))
            else:
                raise NotImplementedError("don't have 3D field plots yet")

        elif isinstance(data, List):
            if target.spatial_dims.ndims == 2:
                renderers.append(ScatterRenderer(data, target))
            else:
                raise NotImplementedError(f"don't have {target.spatial_dims.ndims}D scatter plots yet")

        else:
            raise TypeError(f"unexpected data type: {type(data)}")

    return renderers
