from dataclasses import dataclass

import xarray as xr
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from lib.data.data_with_attrs import Field
from lib.plotting import plt_util
from lib.plotting.frame_data_traits import HasAxes, HasColorNorm, HasFieldData, HasSpatialScales
from lib.plotting.plot_info import ImageInfo, PlotInfo
from lib.plotting.renderer import Renderer
from lib.scale import LinearScale


def get_extent(da: xr.DataArray, dim: str) -> tuple[float, float]:
    lower = da[dim][0]
    upper = da[dim][-1] + (da[dim][1] - da[dim][0])
    return (float(lower), float(upper))


class Field2dRenderer(Renderer[Field]):
    @dataclass(kw_only=True)
    class InitData(HasFieldData, HasSpatialScales, HasColorNorm, HasAxes): ...

    @dataclass(kw_only=True)
    class UpdateData(HasFieldData, HasAxes): ...

    def _transpose(self, data: Field) -> Field:
        spatial_dims = data.metadata.spatial_dims
        return data.with_active_data(data.active_data.transpose(*reversed(spatial_dims)))

    def make_init_data(self, fig: Figure, ax: Axes, frame_data: Field) -> InitData:
        return self.InitData(
            data=frame_data,
            spatial_scales=[LinearScale(), LinearScale()],
            color_norm=LinearScale(),
            color_is_dependent=True,
            axes=ax,
        )

    def init(self, fig: Figure, ax: Axes, full_data: Field, frame_data: Field, init_data: InitData) -> None:
        spatial_dims = frame_data.metadata.spatial_dims
        frame_data = self._transpose(frame_data)
        da = frame_data.active_data

        # must set scale (log, linear) before making image
        ax.set_xscale(init_data.spatial_scales[0])
        ax.set_yscale(init_data.spatial_scales[1])

        self.im = ax.imshow(
            da,
            origin="lower",
            extent=(*get_extent(da, spatial_dims[0]), *get_extent(da, spatial_dims[1])),
            norm=init_data.color_norm,
            interpolation="nearest",
        )

        fig.colorbar(self.im)
        data_lower, data_upper = full_data.var_bounds
        plt_util.update_cbar(self.im, data_min_override=data_lower, data_max_override=data_upper)

        plt_util.update_title(ax, frame_data.metadata, [frame_data.metadata.var_infos[dim].get_coordinate_label(pos) for dim, pos in frame_data.coordss.items() if pos.shape == ()])

        ax.set_aspect(1 / ax.get_data_ratio())
        ax.set_xlabel(frame_data.metadata.var_infos[spatial_dims[0]].to_axis_label())
        ax.set_ylabel(frame_data.metadata.var_infos[spatial_dims[1]].to_axis_label())

    def make_update_data(self, ax: Axes, frame_data: Field) -> UpdateData:
        return self.UpdateData(data=frame_data, axes=ax)

    def draw(self, ax: Axes, frame_data: Field, update_data: UpdateData) -> None:
        frame_data = self._transpose(frame_data)
        self.im.set_data(frame_data.active_data)

        plt_util.update_title(ax, frame_data.metadata, [frame_data.metadata.var_infos[dim].get_coordinate_label(pos) for dim, pos in frame_data.coordss.items() if pos.shape == ()])

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
