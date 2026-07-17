from dataclasses import dataclass

import xarray as xr
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from lib.data.data_with_attrs import Field
from lib.plotting.frame_data_traits import HasAxes, HasFieldData, HasSpatialScales
from lib.plotting.plot_info import ImageInfo, PlotInfo
from lib.plotting.renderer import Renderer
from lib.scale import LinearScale


def get_extent(da: xr.DataArray, dim: str) -> tuple[float, float]:
    lower = da[dim][0]
    upper = da[dim][-1] + (da[dim][1] - da[dim][0])
    return (float(lower), float(upper))


class Field2dRenderer(Renderer[Field]):
    @dataclass(kw_only=True)
    class InitData(HasFieldData, HasSpatialScales, HasAxes): ...

    @dataclass(kw_only=True)
    class UpdateData(HasFieldData, HasAxes): ...

    def _transpose(self, data: Field) -> Field:
        spatial_dims = data.metadata.spatial_dims
        return data.with_active_data(data.active_data.transpose(*reversed(spatial_dims)))

    def make_init_data(self, fig: Figure, ax: Axes, frame_data: Field) -> InitData:
        return self.InitData(
            data=frame_data,
            spatial_scales=[LinearScale(), LinearScale()],
            axes=ax,
        )

    def make_update_data(self, ax: Axes, frame_data: Field) -> UpdateData:
        return self.UpdateData(data=frame_data, axes=ax)

    def init_plot_info(self, full_data: Field, frame_data: Field) -> PlotInfo:
        [x_dim, y_dim] = frame_data.metadata.spatial_dims
        color_dim = frame_data.metadata.active_key

        data = frame_data.active_data.transpose(y_dim, x_dim)

        print(frame_data.metadata.var_infos[color_dim].scale)

        self.plot_info = ImageInfo(
            data=data,
            x_dim=x_dim,
            y_dim=y_dim,
            color_dim=color_dim,
            subject=frame_data.metadata.active_var_info.to_axis_label(),
            dim_scales={
                x_dim: frame_data.metadata.var_infos[x_dim].scale,
                y_dim: frame_data.metadata.var_infos[y_dim].scale,
                color_dim: frame_data.metadata.var_infos[color_dim].scale,
            },
            dim_bounds={
                x_dim: get_extent(data, x_dim),
                y_dim: get_extent(data, y_dim),
                color_dim: full_data.var_bounds,
            },
            dim_displays={
                x_dim: frame_data.metadata.var_infos[x_dim].display,
                y_dim: frame_data.metadata.var_infos[y_dim].display,
                color_dim: None,
            },
            dim_units={
                x_dim: frame_data.metadata.var_infos[x_dim].unit,
                y_dim: frame_data.metadata.var_infos[y_dim].unit,
                color_dim: frame_data.metadata.var_infos[color_dim].unit,
            },
        )

        for dim, coord in frame_data.coordss.items():
            if coord.shape == ():
                self.plot_info.scalar_coord_values[dim] = coord
                self.plot_info.dim_displays[dim] = frame_data.metadata.var_infos[dim].display
                self.plot_info.dim_units[dim] = frame_data.metadata.var_infos[dim].unit

        return self.plot_info

    def update_plot_info(self, frame_data: Field, update_data: UpdateData):
        [x_dim, y_dim] = frame_data.metadata.spatial_dims
        data = frame_data.active_data.transpose(y_dim, x_dim)

        self.plot_info.set("data", data)
        self.plot_info.set("scalar_coord_values", {dim: coord for dim, coord in frame_data.coordss.items() if coord.shape == ()})
