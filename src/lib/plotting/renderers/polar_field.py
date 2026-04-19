from dataclasses import dataclass

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from lib.data.data_with_attrs import Field
from lib.plotting import plt_util
from lib.plotting.frame_data_traits import HasColorNorm, HasFieldData, HasSpatialScales
from lib.plotting.renderer import Renderer


class PolarFieldRenderer(Renderer[Field]):
    @dataclass(kw_only=True)
    class InitData(HasFieldData, HasSpatialScales, HasColorNorm): ...

    @dataclass(kw_only=True)
    class UpdateData(HasFieldData): ...

    def subplot_kw(self):
        return {"projection": "polar"}

    def make_init_data(self, fig, ax, frame_data):
        return self.InitData(
            data=frame_data,
            spatial_scales=["linear", "linear"],
            color_norm="linear",
            color_is_dependent=True,
        )

    def init(self, fig, ax, full_data, frame_data, init_data):
        spatial_dims = frame_data.metadata.spatial_dims

        # must set scale before making image
        ax.set_rscale(init_data.spatial_scales[0])

        vertices_theta = frame_data.coordss[spatial_dims[1]]
        vertices_theta = np.concat([vertices_theta, [vertices_theta[-1] + vertices_theta[1] - vertices_theta[0]]])
        vertices_r = list(frame_data.coordss[spatial_dims[0]])
        vertices_r = np.concat([vertices_r, [vertices_r[-1] + vertices_r[1] - vertices_r[0]]])

        if vertices_theta[0] == 0.0:
            # FIXME hacky check for interpolated values
            # there are two different ways to go from cartesian to polar:
            # - interpolating onto a polar grid, in which case theta coords are "cell centered" (and happen to start at 0)
            # - scattering and binning, in which case theta coords are "node centered" (and happen to start at -pi)
            # this does a half-cell rotation in the former case to transform to "node centered" coords, which matlotlib expects
            vertices_theta -= vertices_theta[1] / 2.0

        self.im = ax.pcolormesh(
            *np.meshgrid(vertices_theta, vertices_r),
            frame_data.active_data,
            shading="flat",
            norm=init_data.color_norm,
        )

        fig.colorbar(self.im)
        data_lower, data_upper = plt_util.get_var_bounds(full_data)
        plt_util.update_cbar(self.im, data_min_override=data_lower, data_max_override=data_upper)

        plt_util.update_title(ax, frame_data.metadata, [frame_data.metadata.dims[dim].get_coordinate_label(pos) for dim, pos in frame_data.coordss.items() if pos.shape == ()])

        # FIXME make the labels work
        # ax.set_xlabel(get_axis_label(spatial_dims[1], frame_data.metadata))
        # ax.set_ylabel(get_axis_label(spatial_dims[0], frame_data.metadata))

    def make_update_data(self, ax, frame_data):
        return self.UpdateData(data=frame_data)

    def draw(self, ax, frame_data, update_data):
        self.im.set_array(frame_data.active_data)

        plt_util.update_title(ax, frame_data.metadata, [frame_data.metadata.dims[dim].get_coordinate_label(pos) for dim, pos in frame_data.coordss.items() if pos.shape == ()])
