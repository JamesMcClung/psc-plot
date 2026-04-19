from dataclasses import dataclass

import xarray as xr
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from lib.data.data_with_attrs import Field
from lib.plotting import plt_util
from lib.plotting.frame_data_traits import HasColorNorm, HasFieldData, HasSpatialScales
from lib.plotting.plt_util import get_axis_label
from lib.plotting.renderer import Renderer


def get_extent(da: xr.DataArray, dim: str) -> tuple[float, float]:
    lower = da[dim][0]
    upper = da[dim][-1] + (da[dim][1] - da[dim][0])
    return (float(lower), float(upper))


class Field2dRenderer(Renderer[Field]):
    @dataclass(kw_only=True)
    class InitData(HasFieldData, HasSpatialScales, HasColorNorm): ...

    @dataclass(kw_only=True)
    class UpdateData(HasFieldData): ...

    def _transpose(self, data: Field) -> Field:
        spatial_dims = data.metadata.spatial_dims
        return data.with_active_data(data.active_data.transpose(*reversed(spatial_dims)))

    def make_init_data(self, fig, ax, frame_data):
        return self.InitData(
            data=frame_data,
            spatial_scales=["linear", "linear"],
            color_norm="linear",
            color_is_dependent=True,
        )

    def init(self, fig, ax, full_data, frame_data, init_data):
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
        )

        fig.colorbar(self.im)
        data_lower, data_upper = full_data.var_bounds
        plt_util.update_cbar(self.im, data_min_override=data_lower, data_max_override=data_upper)

        plt_util.update_title(ax, frame_data.metadata, [frame_data.metadata.dims[dim].get_coordinate_label(pos) for dim, pos in frame_data.coordss.items() if pos.shape == ()])

        ax.set_aspect(1 / ax.get_data_ratio())
        ax.set_xlabel(get_axis_label(spatial_dims[0], frame_data.metadata))
        ax.set_ylabel(get_axis_label(spatial_dims[1], frame_data.metadata))

    def make_update_data(self, ax, frame_data):
        return self.UpdateData(data=frame_data)

    def draw(self, ax, frame_data, update_data):
        frame_data = self._transpose(frame_data)
        self.im.set_data(frame_data.active_data)

        plt_util.update_title(ax, frame_data.metadata, [frame_data.metadata.dims[dim].get_coordinate_label(pos) for dim, pos in frame_data.coordss.items() if pos.shape == ()])
