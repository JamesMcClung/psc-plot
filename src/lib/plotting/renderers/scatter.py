from lib.data.data_with_attrs import FullList
from lib.plotting.plot_info import PlotInfo, ScatterInfo
from lib.plotting.renderer import Renderer


class ScatterRenderer(Renderer[FullList]):
    def init_plot_info(self) -> PlotInfo:
        full_data = self.full_data
        frame_data = self._get_data_at_frame(0)

        [x_dim, y_dim] = frame_data.metadata.spatial_dims

        plot_info = ScatterInfo(
            x_data=frame_data.data[x_dim],
            y_data=frame_data.data[y_dim],
            x_dim=x_dim,
            y_dim=y_dim,
            time_dim=self.plot_target.time_dim,
            subject=f"${frame_data.metadata.subject}$" if frame_data.metadata.subject else None,
            dim_scales={
                x_dim: frame_data.metadata.var_infos[x_dim].scale,
                y_dim: frame_data.metadata.var_infos[y_dim].scale,
            },
            dim_bounds={
                x_dim: full_data.bounds(x_dim),
                y_dim: full_data.bounds(y_dim),
            },
            dim_displays={
                x_dim: frame_data.metadata.var_infos[x_dim].display,
                y_dim: frame_data.metadata.var_infos[y_dim].display,
            },
            dim_units={
                x_dim: frame_data.metadata.var_infos[x_dim].unit,
                y_dim: frame_data.metadata.var_infos[y_dim].unit,
            },
        )

        for dim, coord in frame_data.coordss.items():
            if coord.shape == ():
                plot_info.scalar_coord_values[dim] = coord
                plot_info.dim_displays[dim] = frame_data.metadata.var_infos[dim].display
                plot_info.dim_units[dim] = frame_data.metadata.var_infos[dim].unit

        if color_dim := frame_data.metadata.color_dim:
            plot_info.color_dim = color_dim
            plot_info.color_data = frame_data.data[color_dim]
            plot_info.dim_scales[color_dim] = frame_data.metadata.var_infos[color_dim].scale
            plot_info.dim_bounds[color_dim] = full_data.bounds(color_dim)
            plot_info.dim_displays[color_dim] = frame_data.metadata.var_infos[color_dim].display
            plot_info.dim_units[color_dim] = frame_data.metadata.var_infos[color_dim].unit

        return plot_info

    def update_plot_info(self, frame: int):
        frame_data = self._get_data_at_frame(frame)

        [x_dim, y_dim] = frame_data.metadata.spatial_dims

        self.plot_info.set("x_data", frame_data.data[x_dim])
        self.plot_info.set("y_data", frame_data.data[y_dim])
        self.plot_info.set("scalar_coord_values", {dim: coord for dim, coord in frame_data.coordss.items() if coord.shape == ()})

        if color_dim := self.plot_info.color_dim:
            self.plot_info.set("color_data", frame_data.data[color_dim])
