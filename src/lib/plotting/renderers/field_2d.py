import xarray as xr

from lib.data.data_with_attrs import Field
from lib.plotting.plot_info import ImageInfo, PlotInfo
from lib.plotting.renderer import Renderer


def get_extent(da: xr.DataArray, dim: str) -> tuple[float, float]:
    lower = da[dim][0]
    upper = da[dim][-1] + (da[dim][1] - da[dim][0])
    return (float(lower), float(upper))


class Field2dRenderer(Renderer[Field]):
    def _transpose(self, data: Field) -> Field:
        spatial_dims = data.metadata.spatial_dims
        return data.with_active_data(data.active_data.transpose(*reversed(spatial_dims)))

    def init_plot_info(self) -> PlotInfo:
        full_data = self.full_data
        frame_data = self._get_data_at_frame(0)

        [x_dim, y_dim] = frame_data.metadata.spatial_dims
        color_dim = frame_data.metadata.active_key

        data = frame_data.active_data.transpose(y_dim, x_dim)

        plot_info = ImageInfo(
            data=data,
            x_dim=x_dim,
            y_dim=y_dim,
            color_dim=color_dim,
            time_dim=self.plot_target.time_dim,
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
                plot_info.scalar_coord_values[dim] = coord
                plot_info.dim_displays[dim] = frame_data.metadata.var_infos[dim].display
                plot_info.dim_units[dim] = frame_data.metadata.var_infos[dim].unit

        return plot_info

    def update_plot_info(self, frame: int):
        frame_data = self._get_data_at_frame(frame)

        [x_dim, y_dim] = frame_data.metadata.spatial_dims
        data = frame_data.active_data.transpose(y_dim, x_dim)

        self.plot_info.set("data", data)
        self.plot_info.set("scalar_coord_values", {dim: coord for dim, coord in frame_data.coordss.items() if coord.shape == ()})
